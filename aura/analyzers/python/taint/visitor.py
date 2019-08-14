import pprint
import fnmatch
from pathlib import Path

from ..nodes import *
from ..visitor import Visitor
from ..rewrite_ast import ASTRewrite
from .... import config


class TaintAnalysis(Visitor):
    def load_tree(self, source: Path):
        if self.tree is None:
            cached = ASTRewrite.from_cache(source=source, metadata=self.metadata)
            if not cached.traversed:
                cached.traverse()
            self.tree = cached.tree
            del cached

    def _visit_node(self, context:Context):
        if not isinstance(context.node, ASTNode):
            return
        elif isinstance(context.node, Import):
            return

        funcs = (
            self.__mark_flask_route,
            self.__mark_sinks,
            self.__mark_sources,
            self.__propagate_taint,
        )

        for x in funcs:
            x(context=context)
            if context.visitor.modified:
                return

    def __mark_flask_route(self, context):
        if not isinstance(context.node, FunctionDef):
            return

        if not len(context.node.decorator_list) > 0:
            return

        for dec in context.node.decorator_list:
            if isinstance(dec, Call) and isinstance(dec.func, Attribute) and dec.func.attr == 'route':
                if 'flask_route' not in context.node.tags:
                    context.node.tags.add('flask_route')
                    context.visitor.modified = True
                    return

    def __mark_sinks(self, context):
        f_name = context.node.full_name
        if f_name is None:
            return
        elif 'taint_sink' in context.node.tags:
            return
        elif not isinstance(f_name, str):
            return

        for sink in config.SEMANTIC_RULES.get('taint_sinks', []):
            if sink == f_name or fnmatch.fnmatch(f_name, sink):
                context.node.tags.add('taint_sink')
                context.visitor.modified = True
                return

    def __mark_sources(self, context):
        f_name = context.node.full_name

        if not (isinstance(f_name, str) and 'taint_source' not in context.node.tags):
            return

        for source in config.SEMANTIC_RULES.get('taint_sources', []):
            if source.rstrip('.*') == f_name or fnmatch.fnmatch(f_name, source):
                context.node.tags.add('taint_source')
                context.node._taint_class = Taints.TAINTED
                context.visitor.modified = True
                return

    def __propagate_taint(self, context):
        if isinstance(context.node, Attribute) and isinstance(context.node.source, ASTNode):
            t = context.node.source._taint_class

            if 'taint_source' in context.node.source.tags and context.node._taint_class != Taints.TAINTED:
                context.node._taint_class = Taints.TAINTED
                context.visitor.modified = True
                return
            elif t != Taints.UNKNOWN and t != context.node._taint_class:
                context.node._taint_class = t
                context.visitor.modified = True
                return
        elif isinstance(context.node, Call):
            f_name = context.node.full_name

            args_taints = []
            for x in context.node.args:
                if isinstance(x, ASTNode):
                    args_taints.append(x._taint_class)
            for x in context.node.kwargs.values():
                if isinstance(x, ASTNode):
                    args_taints.append(x._taint_class)

            if isinstance(context.node.func, ASTNode):
                args_taints.append(context.node.func._taint_class)

            if not args_taints:
                return

            call_taint = max(args_taints)
            if call_taint > context.node._taint_class:
                context.node._taint_class = call_taint
                context.visitor.modified = True
                return

            if isinstance(f_name, str) and f_name in context.call_graph.definitions:
                func_def = context.call_graph.definitions[f_name]
                for x in context.node.args:
                    func_def.set_taint(x.full_name, x._taint_class, context)
                    pass

        elif isinstance(context.node, Var):
            var_taint = max(
                context.node._taint_class,
                getattr(context.node.value, '_taint_class', Taints.UNKNOWN)
            )

            if var_taint != context.node._taint_class:
                context.node._taint_class = var_taint
                context.visitor.modified = True
                return

        elif isinstance(context.node, Subscript):
            if not isinstance(context.node.value, ASTNode):
                return

            if context.node.value._taint_class > context.node._taint_class:
                context.node._taint_class = context.node.value._taint_class
                context.visitor.modified = True
                return
        elif isinstance(context.node, ReturnStmt) and isinstance(context.node.value, ASTNode):
            if context.node.value._taint_class > context.node._taint_class:
                context.node._taint_class = context.node.value._taint_class
                context.visitor.modified = True
                return
        elif isinstance(context.node, BinOp):
            taints = []

            if isinstance(context.node.left, Arguments):
                t_arg = context.node.left.taints.get(context.node._orig_left, Taints.SAFE)
                if t_arg > context.node._taint_class:
                    context.node._taint_class = t_arg
                    context.visitor.modified = True
            elif isinstance(context.node.left, ASTNode):
                taints.append(context.node.left._taint_class)

            if isinstance(context.node.right, Arguments):
                t_arg = context.node.right.taints.get(context.node._orig_right, Taints.SAFE)
                if t_arg > context.node._taint_class:
                    context.node._taint_class = t_arg
                    context.visitor.modified = True
            elif isinstance(context.node.right, ASTNode):
                taints.append(context.node.right._taint_class)

            if not taints:
                return

            op_taint = max(taints)
            if op_taint > context.node._taint_class:
                context.node._taint_class = op_taint
                context.visitor.modified = True
                return

        elif isinstance(context.node, FunctionDef):
            f_name = context.node.full_name

            if f_name in context.call_graph:
                callers = context.call_graph[f_name]
                for c in callers:
                    pass # TODO
