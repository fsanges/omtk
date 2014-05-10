'''
A module that convert mathematical formulas to utility nodes.
Ex:
    from omtk.rigging import formulaParser
    grp = pymel.createNode('transform')
    formulaParser.parse('(tx*rx)+(ty*ry)+(tz*rz)', tx=loc.tx, ty=loc.ty, tz=loc.tz, rx=loc.rx, ry=loc.ry, rz=loc.rz)
'''
# TODO: Implement operators priotity

import re, math
from omtk.libs import libRigging
import pymel.core as pymel

class operator(object):
    @classmethod
    def execute(self, *args, **kwargs):
        raise NotImplementedError
    @classmethod
    def create(self, *args, **kwargs):
        raise NotImplementedError

class add(operator):
    def execute(self, arg1, arg2):
        return arg1 + arg2
    def create(self, arg1, arg2):
        return libRigging.CreateUtilityNode('plusMinusAverage', operation=1, input1D=[arg1, arg2]).output1D

class substract(operator):
    def execute(self, arg1, arg2):
        return arg1 - arg2
    def create(self, arg1, arg2):
        return libRigging.CreateUtilityNode('plusMinusAverage', operation=2, input1D=[arg1, arg2]).output1D

class multiply(operator):
    def execute(arg1, arg2):
        return arg1 * arg2;
    def create(self, arg1, arg2):
        return libRigging.CreateUtilityNode('multiplyDivide', operation=1, input1X=arg1, input2X=arg2).outputX

class divide(operator):
    def execute(self, arg1, arg2):
        return arg1 / arg2;
    def create(self, arg1, arg2):
        return libRigging.CreateUtilityNode('multiplyDivide', operation=2, input1X=arg1, input2X=arg2).outputX

class pow(operator):
    def execute(self, arg1, arg2):
        return math.pow(arg1, arg2);
    def create(self, arg1, arg2):
        return libRigging.CreateUtilityNode('multiplyDivide', operation=3, input1X=arg1, input2X=arg2).outputX

class distance(operator):
    def execute(self, arg1, arg2):
        return arg1 * arg2;
    def create(self, arg1, arg2):
        return libRigging.CreateUtilityNode('distance', inMatrix1=arg1, inMatrix2=arg2).distance

class equal(operator):
    def execute(self, arg1, arg2):
        return arg1 == arg2;
    def create(self, arg1, arg2):
        return libRigging.CreateUtilityNode('condition', operation=0, colorIfTrue=1.0, colorIfFalse=0.0).outColorR

class not_equal(operator):
    def execute(self, arg1, arg2):
        return arg1 != arg2;
    def create(self, *args, **kwargs):
        return equal(operation=1).outColorR

class bigger(operator):
    def execute(self, arg1, arg2):
        return arg1 > arg2
    def create(self, *args, **kwargs):
        return equal(operation=2, *args, **kwargs).outColorR

class bigger_or_equal(operator):
    def execute(self, arg1, arg2):
        return arg1 >= arg2;
    def create(self, *args, **kwargs):
        return equal(operation=3, *args, **kwargs).outColorR

class smaller(operator):
    def execute(self, arg1, arg2):
        return arg1 < arg2;
    def create(self, *args, **kwargs):
        return equal(operation=4, *args, **kwargs).outColorR

class smaller_or_equal(operator):
    def execute(self, arg1, arg2):
        return arg1 <= arg2;
    def create(self, *args, **kwargs):
        return equal(operation=5, *args, **kwargs).outColorR

operators = {
    '+': add(),
    '-': substract(),
    '*': multiply(),
    '/': divide(),
    '^': pow(),
    '~': distance(),
    '=': equal(),
    '!=': not_equal(),
    '>': bigger(),
    '>=' : bigger_or_equal(),
    '<': smaller(),
    '<=': smaller_or_equal()
}

_varDelimiters = ['0','1','2','3','4','5','6','7','8','9','(',')', '.'] + operators.keys()
regex_splitVariables = '|'.join(re.escape(str) for str in _varDelimiters)

dicVariables = {}

def convert_basic_value(str):
    # handle parenthesis
    if isinstance(str, list):
        return create_utilityNodes(*str)

    # try float conversion
    try:
        return float(str)
    except: pass

    # try int conversion
    try:
        return int(str)
    except: pass

    # try variable swapping
    global dicVariables
    if str in dicVariables:
        return dicVariables[str]

    return str

def can_optimise(*args):
    for arg in args:
        if isinstance(arg, pymel.Attribute):
            return False
    return True

def create_utilityNodes(*args):
    args = list(args) # cast tuple to list
    num_args = len(args)
    return_val = None
    for i in range(1, num_args-1):
        perArg = args[i]
        if perArg in operators:
            preArg = convert_basic_value(args[i-1])
            posArg = convert_basic_value(args[i+1])
            cls = operators[perArg]
            fn = cls.execute if can_optimise(preArg, posArg) else cls.create
            return_val = args[i+1] = fn(preArg, posArg)
            args[i-1] = None
            args[i] = None
    return return_val

def parse(str, **kwargs):
    # step 1: identify variables
    vars = (var.strip() for var in re.split(regex_splitVariables, str))
    vars = filter(lambda x: x, vars)
    #print 'found vars:', vars

    # step 2: ensure all variables are defined
    # todo: validate vars types
    global dicVariables
    dicVariables = {}
    for var in vars:
        if not var in kwargs:
            raise KeyError("Variable '{0}' is not defined".format(var))
        dicVariables[var] = kwargs[var]
    #print 'defined variables are:', dicVariables

    # Convert parenthesis and operators to nested string lists
    # src: http://stackoverflow.com/questions/5454322/python-how-to-match-nested-parentheses-with-regex
    from omtk.deps import pyparsing # make sure you have this installed
    content = pyparsing.Word(pyparsing.alphanums + '.')
    for op in operators.keys(): content |= op # defined operators
    nestedExpr = pyparsing.nestedExpr( opener='(', closer=')', content=content)
    #print 'parsing:', str
    res = nestedExpr.parseString('({0})'.format(str)) # wrap all string in parenthesis, or it won't work
    nested_tokens = res.asList()[0]

    #print 'tokens', nested_tokens

    return create_utilityNodes(*nested_tokens)

'''
ex: basic_squash
parse("1 / stretch", stretch=xstretch)

ex: complex squash (f=[0.0-1.0])
parse("1 / stretch ^ (1 / (e^(x^2)))", e=math.e, x=f, stretch=stretch)

'''