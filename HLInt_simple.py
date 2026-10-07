# HLInt.XXX - simple interpreter for the HL language
# How to run:  python HLInt_simple.py PROG1.HL

import sys

RESERVED = ["integer", "double", "if", "output"]

# these are shared by the functions below
types = {}       # variable name -> "integer" or "double"
assigned = []    # variables that already have a value
values = {}      # variable name -> its value (used when running)
errors = []      # list of error messages


# ---------------------------------------------------------------
# STEP 1: remove spaces
# ---------------------------------------------------------------
def remove_spaces(text):
    result = ""
    for ch in text:
        if ch != " " and ch != "\t":
            result = result + ch
    return result


# ---------------------------------------------------------------
# STEP 2: write reserved words and symbols to RES_SYM.TXT
# ---------------------------------------------------------------
def write_res_sym(clean_lines):
    out = open("RES_SYM.TXT", "w")
    in_string = False
    for c in clean_lines:
        i = 0
        while i < len(c):
            ch = c[i]
            if ch == '"':
                out.write('"\tSYMBOL\n')
                in_string = not in_string      # skip the stuff inside quotes
                i = i + 1
            elif in_string:
                i = i + 1
            elif ch.isalpha():
                word = ""
                while i < len(c) and (c[i].isalnum() or c[i] == "_"):
                    word = word + c[i]
                    i = i + 1
                if word.lower() in RESERVED:
                    out.write(word.lower() + "\tRESERVED WORD\n")
            elif ch in ":=!<":
                pair = c[i:i + 2]
                if pair in [":=", "==", "!=", "<<"]:
                    out.write(pair + "\tSYMBOL\n")
                    i = i + 2
                else:
                    if ch != "!":
                        out.write(ch + "\tSYMBOL\n")
                    i = i + 1
            elif ch in ";()+->":
                out.write(ch + "\tSYMBOL\n")
                i = i + 1
            else:
                i = i + 1
        in_string = False
    out.close()


# ---------------------------------------------------------------
# helper functions for checking
# ---------------------------------------------------------------
def is_number(s):
    # single digit integer (like 5) or double with at most 2 decimals (like 2.35)
    if s == "":
        return False
    for ch in s:
        if ch not in "0123456789.":
            return False
    dots = s.count(".")
    if dots > 1:
        return False
    if dots == 1:
        left, right = s.split(".")
        if left == "" or right == "" or len(right) > 2:
            return False
        return True
    return len(s) == 1


def is_name(s):
    if s == "" or not (s[0].isalpha() or s[0] == "_"):
        return False
    for ch in s:
        if not (ch.isalnum() or ch == "_"):
            return False
    if s.lower() in RESERVED:
        return False
    return True


def split_terms(expr):
    # "x+2-y" -> terms ["x","2","y"], ops ["+","-"]
    terms = []
    ops = []
    current = ""
    for ch in expr:
        if ch == "+" or ch == "-":
            terms.append(current)
            ops.append(ch)
            current = ""
        else:
            current = current + ch
    terms.append(current)
    return terms, ops


def check_expr(expr, n):
    # returns "integer" or "double", or None if there is an error
    terms, ops = split_terms(expr)
    result_type = "integer"
    for t in terms:
        if t == "":
            errors.append("Line " + str(n) + ": missing number or variable")
            return None
        if is_number(t):
            if "." in t:
                result_type = "double"
        elif is_name(t):
            if t not in types:
                errors.append("Line " + str(n) + ": variable '" + t + "' is not declared")
                return None
            if t not in assigned:
                errors.append("Line " + str(n) + ": variable '" + t + "' has no value yet")
                return None
            if types[t] == "double":
                result_type = "double"
        else:
            errors.append("Line " + str(n) + ": '" + t + "' is not valid (use single digit "
                          "integers, doubles with 2 decimals, or variables)")
            return None
    return result_type


# ---------------------------------------------------------------
# STEP 3: check one statement. Returns a tuple that describes it,
# or None if there is an error.
# ---------------------------------------------------------------
def check_statement(c, original, n):
    low = c.lower()
    if not c.endswith(";"):
        errors.append("Line " + str(n) + ": missing ';'")
        return None
    body = c[:-1]    # statement without the ;

    # output statement
    if low.startswith("output<<"):
        rest = body[8:]
        if rest.startswith('"'):
            if len(rest) < 2 or not rest.endswith('"'):
                errors.append("Line " + str(n) + ": missing closing quote")
                return None
            first = original.find('"')
            last = original.rfind('"')
            return ("text", original[first + 1:last])
        if check_expr(rest, n) is None:
            return None
        return ("expr", rest)

    # declaration  x:integer;
    if ":" in body and ":=" not in body:
        parts = body.split(":")
        if len(parts) != 2:
            errors.append("Line " + str(n) + ": bad declaration")
            return None
        name = parts[0]
        kind = parts[1].lower()
        if not is_name(name):
            errors.append("Line " + str(n) + ": '" + name + "' is not a valid variable name")
            return None
        if kind != "integer" and kind != "double":
            errors.append("Line " + str(n) + ": data type must be integer or double")
            return None
        if name in types:
            errors.append("Line " + str(n) + ": variable '" + name + "' declared twice")
            return None
        types[name] = kind
        return ("decl", name, kind)

    # assignment  x:=5;
    if ":=" in body:
        name, expr = body.split(":=", 1)
    elif "=" in body:
        name, expr = body.split("=", 1)
    else:
        errors.append("Line " + str(n) + ": unknown statement")
        return None
    if name not in types:
        errors.append("Line " + str(n) + ": variable '" + name + "' is not declared")
        return None
    expr_type = check_expr(expr, n)
    if expr_type is None:
        return None
    if expr_type == "double" and types[name] == "integer":
        errors.append("Line " + str(n) + ": cannot put a double value in integer '" + name + "'")
        return None
    assigned.append(name)
    return ("assign", name, expr)


# ---------------------------------------------------------------
# STEP 4: go through the whole program
# ---------------------------------------------------------------
def check_program(lines, clean_lines):
    program = []
    i = 0
    while i < len(clean_lines):
        c = clean_lines[i]
        n = i + 1
        if c == "":
            i = i + 1
            continue

        if c.lower().startswith("if("):
            close = c.find(")")
            if close == -1:
                errors.append("Line " + str(n) + ": missing ')' in if")
                i = i + 1
                continue
            cond = c[3:close]
            op = ""
            for o in ["==", "!=", "<", ">"]:
                if o in cond:
                    op = o
                    break
            if op == "":
                errors.append("Line " + str(n) + ": condition needs >, <, == or !=")
                i = i + 1
                continue
            left, right = cond.split(op, 1)
            left_ok = check_expr(left, n)
            right_ok = check_expr(right, n)

            # the statement after the if (same line, or the next line)
            rest = c[close + 1:]
            original = lines[i]
            if rest == "":
                i = i + 1
                while i < len(clean_lines) and clean_lines[i] == "":
                    i = i + 1
                if i >= len(clean_lines):
                    errors.append("Line " + str(n) + ": no statement after if")
                    break
                rest = clean_lines[i]
                original = lines[i]
            if rest.lower().startswith("if("):
                errors.append("Line " + str(i + 1) + ": only one-way if is allowed")
            else:
                stmt = check_statement(rest, original, i + 1)
                if stmt is not None and stmt[0] == "decl":
                    errors.append("Line " + str(i + 1) + ": declaration not allowed inside if")
                elif stmt is not None and left_ok is not None and right_ok is not None:
                    program.append(("if", left, op, right, stmt))
        else:
            stmt = check_statement(c, lines[i], n)
            if stmt is not None:
                program.append(stmt)
        i = i + 1
    return program


# ---------------------------------------------------------------
# STEP 5: run the program
# ---------------------------------------------------------------
def get_value(t):
    if is_number(t):
        if "." in t:
            return float(t)
        return int(t)
    return values[t]


def eval_expr(expr):
    terms, ops = split_terms(expr)
    total = get_value(terms[0])
    for k in range(len(ops)):
        if ops[k] == "+":
            total = total + get_value(terms[k + 1])
        else:
            total = total - get_value(terms[k + 1])
    if isinstance(total, float):
        total = round(total, 2)
    return total


def show(v):
    if isinstance(v, float):
        return "%.2f" % v
    return str(v)


def run_statement(s):
    kind = s[0]
    if kind == "decl":
        pass
    elif kind == "assign":
        v = eval_expr(s[2])
        if types[s[1]] == "double":
            values[s[1]] = float(v)
        else:
            values[s[1]] = int(v)
    elif kind == "text":
        print(s[1])
    elif kind == "expr":
        print(show(eval_expr(s[1])))
    elif kind == "if":
        a = eval_expr(s[1])
        b = eval_expr(s[3])
        op = s[2]
        ok = False
        if op == "<" and a < b:
            ok = True
        elif op == ">" and a > b:
            ok = True
        elif op == "==" and a == b:
            ok = True
        elif op == "!=" and a != b:
            ok = True
        if ok:
            run_statement(s[4])


# ---------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------
if len(sys.argv) > 1:
    filename = sys.argv[1]
else:
    filename = input("Enter source file (example PROG1.HL): ")

try:
    f = open(filename, "r", encoding="utf-8")
    text = f.read()
    f.close()
except OSError:
    print("Cannot open file " + filename)
    sys.exit()

text = text.replace("\u201c", '"').replace("\u201d", '"')   # curly quotes
lines = text.split("\n")

# remove the spaces and save to NOSPACES.TXT
clean_lines = []
for line in lines:
    clean_lines.append(remove_spaces(line.replace("\r", "")))
out = open("NOSPACES.TXT", "w")
out.write("\n".join(clean_lines))
out.close()

# reserved words and symbols
write_res_sym(clean_lines)

# check for errors
program = check_program(lines, clean_lines)

if len(errors) > 0:
    print("ERROR")
    for e in errors:
        print("  " + e)
else:
    print("NO ERROR(S) FOUND")
    for s in program:
        run_statement(s)
