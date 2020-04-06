from .visitor import Visitor
from .nodes import *


def visit_List(context):
    new_node = List(elts=context.node.get("elts", []), ctx=context.node.get("ctx"))
    new_node.line_no = context.node["lineno"]
    new_node.col = context.node["col_offset"]
    context.replace(new_node)


def visit_Str(context):
    node = String(context.node["s"])
    node.line_no = context.node["lineno"]
    node.col = context.node["col_offset"]
    context.replace(node)


def visit_Num(context):
    node = Number(context.node["n"])
    node.line_no = context.node["lineno"]
    node.col = context.node["col_offset"]
    context.replace(node)


def visit_Dict(context):
    context.replace(Dictionary(context.node["keys"], context.node["values"]))


def visit_Expr(context):
    context.replace(context.node["value"])


def visit_Call(context):
    keyword = {}
    for x in context.node["keywords"]:
        keyword[x["arg"]] = x["value"]

    new_node = Call(context.node["func"], context.node["args"], keyword)
    new_node.line_no = context.node["lineno"]
    new_node.col = context.node["col_offset"]
    new_node._docs = context.node.get("_doc_string")
    context.replace(new_node)


def visit_Assign(context):
    # TODO: fixme when len(targets) > 1
    target = context.node["targets"][0]

    if isinstance(target, Var) and target.var_type == "name":
        target = target.name()

    new_node = Var(target, context.node["value"])
    new_node.line_no = context.node["lineno"]
    context.replace(new_node)


def visit_BinOp(context):
    left = context.node["right"]
    right = context.node["left"]
    new_node = BinOp(left=left, right=right, op=context.node["op"]["_type"].lower())
    new_node.line_no = context.node["lineno"]
    context.replace(new_node)


def visit_Name(context):
    # TODO: check if we need to store node['ctx']['_type']
    # context.replace(Var(context.node['id'], var_type="name"))
    context.replace(context.node["id"])


def visit_Attribute(context):
    target = context.node["value"]
    if isinstance(target, Var) and target.var_type == "name":
        target = target.name()

    new_node = Attribute(target, context.node["attr"], context.node["ctx"]["_type"])
    new_node.line_no = context.node["lineno"]
    new_node.col = context.node["col_offset"]

    context.replace(new_node)


def visit_ImportFrom(context):
    new_node = Import()
    new_node.level = context.node.get("level")
    new_node.line_no = context.node["lineno"]
    new_node.col = context.node["col_offset"]

    for x in context.node["names"]:
        alias = x["asname"] if x["asname"] else x["name"]
        mname = context.node['module'] or ''
        new_node.names[alias] = f"{mname}.{x['name']}"

    context.replace(new_node)


def visit_Import(context):
    new_node = Import()
    new_node.line_no = context.node["lineno"]
    new_node.col = context.node["col_offset"]

    for x in context.node["names"]:
        alias = x["asname"] if x.get("asname") else x["name"]
        new_node.names[alias] = x["name"]

    context.replace(new_node)


def visit_Print(context):
    new_node = Print(context.node["values"], context.node["dest"])
    new_node._original = context.node
    context.replace(new_node)


def visit_Compare(context):
    new_node = Compare(
        left=context.node["left"],
        ops=context.node["ops"],
        comparators=context.node["comparators"]
    )

    if context.node.get('body'):
        new_node.body = context.node['body']

    if context.node.get('orelse'):
        new_node.orelse = context.node['orelse']

    new_node._original = context.node
    context.replace(new_node)


def visit_FunctionDef(context):
    new_node = FunctionDef(
        name=context.node["name"],
        args=context.node["args"],
        body=context.node["body"],
        decorator_list=context.node["decorator_list"],
        returns=context.node.get("returns"),
    )
    new_node._original = context.node
    new_node.line_no = context.node["lineno"]
    context.replace(new_node)


def visit_arguments(context):
    args = []
    if context.node.get("args"):
        for x in context.node["args"]:
            if isinstance(x, dict) and "arg" in x:
                args.append(x["arg"])
            else:
                args.append(x)

    if (
        isinstance(context.node.get("kwarg"), dict)
        and context.node["kwarg"].get("_type") == "arg"
    ):
        kwarg = context.node["kwarg"]["arg"]
    else:
        kwarg = context.node.get("kwarg")

    new_node = Arguments(
        args=args,
        vararg=context.node.get("varargs"),
        kwonlyargs=context.node.get("kwonlyarg", []),
        kwarg=kwarg,
        defaults=context.node.get("defaults", []),
        kw_defaults=context.node.get("kw_defaults", []),
    )
    context.replace(new_node)


def visit_ClassDef(context):
    new_node = ClassDef(
        name=context.node.get("name"),
        body=context.node.get("body"),
        bases=context.node.get("bases"),
    )
    new_node.line_no = context.node.get("lineno")
    new_node.col = context.node.get("col_offset", 0)
    context.replace(new_node)


def visit_Return(context):
    new_node = ReturnStmt(value=context.node["value"])
    new_node.line_no = context.node["lineno"]
    context.replace(new_node)


def visit_Yield(context):
    new_node = Yield(value=context.node["value"])
    new_node.line_no = context.node["lineno"]
    new_node.col = context.node["col_offset"]
    context.replace(new_node)


def visit_YieldFrom(context):
    new_node = YieldFrom(value=context.node["value"])
    new_node.line_no = context.node["lineno"]
    new_node.col = context.node["col_offset"]
    context.replace(new_node)


def visit_Subscript(context):
    new_node = Subscript(
        value=context.node.get("value"),
        slice=context.node.get("slice"),
        ctx=context.node["ctx"]["_type"],
    )
    new_node.line_no = context.node["lineno"]
    context.replace(new_node)


def visit_Continue(context):
    new_node = Continue()
    new_node.line_no = context.node["lineno"]
    new_node.col = context.node["col_offset"]
    context.replace(new_node)


def visit_Pass(context):
    new_node = Pass()
    new_node.line_no = context.node["lineno"]
    new_node.col = context.node["col_offset"]
    context.replace(new_node)


def visit_ExceptHandler(context):
    new_node = ExceptHandler(
        body=context.node.get("body", []),
        type=context.node.get("type"),
        name=context.node.get("name"),
    )
    new_node.line_no = context.node["lineno"]
    new_node.col = context.node["col_offset"]
    context.replace(new_node)


VISITORS = {
    "List": visit_List,
    "Tuple": visit_List,
    "Set": visit_List,
    "Str": visit_Str,
    "Num": visit_Num,
    "Dict": visit_Dict,
    "Expr": visit_Expr,
    "Call": visit_Call,
    "Assign": visit_Assign,
    "BinOp": visit_BinOp,
    "Name": visit_Name,
    "Attribute": visit_Attribute,
    "ImportFrom": visit_ImportFrom,
    "Import": visit_Import,
    "Print": visit_Print,
    "Compare": visit_Compare,
    "FunctionDef": visit_FunctionDef,
    "ClassDef": visit_ClassDef,
    "Return": visit_Return,
    "Yield": visit_Yield,
    "YieldFrom": visit_YieldFrom,
    "Subscript": visit_Subscript,
    "arguments": visit_arguments,
    "Continue": visit_Continue,
    "Pass": visit_Pass,
    "ExceptHandler": visit_ExceptHandler,
}


class ASTVisitor(Visitor):
    """
    This class converts JSON serialized AST tree to appropriate dataclasses if possible
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _visit_node(self, context):
        if type(context.node) != dict:
            return

        otype = context.node.get("_type")

        if otype in VISITORS:
            VISITORS[otype](context)
