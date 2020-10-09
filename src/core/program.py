#
# program.py
#
# the pashmak project
# Copyright 2020 parsa mpsh <parsampsh@gmail.com>
#
# This file is part of pashmak.
#
# pashmak is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pashmak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pashmak.  If not, see <https://www.gnu.org/licenses/>.
##################################################

''' Pashmak program object '''

import sys
import os
import signal
from syntax import parser
from core import helpers

class Program(helpers.Helpers):
    ''' Pashmak program object '''

    def __init__(self, is_test=False, args=[]):
        self.variables = {} # main state variables
        self.states = [] # list of states
        self.functions = {
            "mem": [] # mem is a empty function just for save mem in code
        } # declared functions <function-name>:[<list-of-body-operations>]
        self.operations = [] # list of operations
        self.sections = {} # list of declared sections <section-name>:<index-of-operation-to-jump>
        self.mem = None # memory temp value
        self.is_test = is_test # program is in testing state
        self.output = '' # program output (for testing state)
        self.runtime_error = None # program raised error (for testing state)
        self.is_in_try = None # says program is in try-endtry block
        self.runed_functions = [] # runed functions for stop function multi calling in one operation
        self.current_namespace = '' # current namespace prefix to add it before name of functions
        self.used_namespaces = [] # list of used namespaces
        self.included_modules = [] # list of included modules to stop repeating imports

        self.current_step = 0
        self.main_filename = os.getcwd() + '/a'

        # set argument variables
        self.set_var('argv', args)
        self.set_var('argc', len(self.get_var('argv')))

    def set_operations(self, operations: list):
        ''' Set operations list '''
        # include stdlib before everything
        tmp = parser.parse('mem "@stdlib"; include ^;')
        operations.insert(0, tmp[0])
        operations.insert(1, tmp[1])

        # set operations on program object
        self.operations = operations

    def set_operation_index(self, op: dict) -> dict:
        ''' Add operation index to operation dictonary '''
        op['index'] = self.current_step
        return op

    def get_mem(self):
        ''' Return memory value and empty that '''
        mem = self.mem
        self.mem = None
        return mem

    def update_section_indexes(self, after_index):
        '''
        When a new operation inserted in operations list,
        this function add 1 to section indexes to be
        sync with new operations list
        '''
        for k in self.sections:
            if self.sections[k] > after_index:
                self.sections[k] = self.sections[k] + 1

    def raise_error(self, error_type: str, message: str, op: dict):
        ''' Raise error in program '''
        # check is in try
        if self.is_in_try != None:
            section_index = self.is_in_try
            self.is_in_try = None
            new_step = self.sections[str(section_index)]
            self.current_step = new_step-1

            # put error data in mem
            self.mem = {'type': error_type, 'message': message, 'index': op['index']}
            return
        # raise error
        if self.is_test:
            self.runtime_error = [error_type, message, op]
            return

        # render error
        print(error_type + ': ' + message + ':')
        for state in self.states:
            try:
                tmp_op = self.operations[state['entry_point']]
                print('\tin ' + str(tmp_op['index']) + ': ' + tmp_op['str'])
            except KeyError:
                pass
        print('\tin ' + str(op['index']) + ': ' + op['str'])
        sys.exit(1)

    def exec_func(self, func_body: list, with_state=True):
        ''' Gets a list from operations and runs them as function or included script '''
        # create new state for this call
        if with_state:
            self.states.append({
                'entry_point': self.current_step,
                'vars': dict(self.variables),
            })

        # check function already called in this point
        if self.current_step in self.runed_functions and with_state:
            return

        # add this point to runed functions (for stop repeating call in loops)
        if with_state:
            self.runed_functions.append(self.current_step)

        # run function
        i = int(self.current_step)
        is_in_func = False
        for func_op in func_body:
            func_op_parsed = self.set_operation_index(func_op)
            if func_op_parsed['command'] == 'section' and not is_in_func:
                section_name = func_op_parsed['args'][0]
                self.sections[section_name] = i+1
            else:
                if func_op_parsed['command'] == 'func':
                    is_in_func = True
                elif func_op_parsed['command'] == 'endfunc':
                    is_in_func = False
                self.operations.insert(i+1, func_op)
                self.update_section_indexes(i+1)
                i += 1

        if with_state:
            self.operations.insert(i+1, parser.parse('popstate')[0])
            self.update_section_indexes(i+1)

    def run(self, op: dict):
        ''' Run once operation '''

        op = self.set_operation_index(op)
        op_name = op['command']

        if op_name == 'endfunc':
            self.run_endfunc(op)
            return

        if op_name == 'popstate':
            if self.states:
                self.states.pop()
            return

        # if a function is started, append current operation to the function body
        try:
            tmp = self.current_func
            self.functions[self.current_func].append(op)
            return
        except NameError:
            pass
        except KeyError:
            pass
        except AttributeError:
            pass

        if op_name == 'set':
            self.run_set(op)
            return
        elif op_name == 'free':
            self.run_free(op)
            return
        elif op_name == 'copy':
            self.run_copy(op)
            return
        elif op_name == 'out':
            self.run_out(op)
            return
        elif op_name == 'read':
            self.run_read(op)
            return
        elif op_name == 'return':
            self.run_return(op)
            return
        elif op_name == 'func':
            self.run_func(op)
            return
        elif op_name == 'required':
            self.run_required(op)
            return
        elif op_name == 'typeof':
            self.run_typeof(op)
            return
        elif op_name == 'system':
            self.run_system(op)
            return
        elif op_name == 'include':
            self.run_include(op)
            return
        elif op_name == 'goto':
            self.run_goto(op)
            return
        elif op_name == 'gotoif':
            self.run_gotoif(op)
            return
        elif op_name == 'fread':
            self.run_fread(op)
            return
        elif op_name == 'fwrite':
            self.run_fwrite(op)
            return
        elif op_name == 'chdir':
            self.run_chdir(op)
            return
        elif op_name == 'cwd':
            self.run_cwd(op)
            return
        elif op_name == 'isset':
            self.run_isset(op)
            return
        elif op_name == 'try':
            self.run_try(op)
            return
        elif op_name == 'endtry':
            self.run_endtry(op)
            return
        elif op_name == 'eval':
            self.run_eval(op)
            return
        elif op_name == 'arraypush':
            self.run_arraypush(op)
            return
        elif op_name == 'arraypop':
            self.run_arraypop(op)
            return
        elif op_name == 'python':
            self.run_python(op)
            return
        elif op_name == 'namespace':
            self.run_namespace(op)
            return
        elif op_name == 'endnamespace':
            self.run_endnamespace(op)
            return
        elif op_name == 'use':
            self.run_use(op)
            return
        elif op_name == 'pass':
            return



        # check function exists
        try:
            func_body = self.functions[self.current_namespace + op_name]
        except KeyError:
            func_body = None
            for used_namespace in self.used_namespaces:
                try:
                    func_body = self.functions[used_namespace + '.' + op_name]
                except KeyError:
                    pass
            if not func_body:
                try:
                    func_body = self.functions[op_name]
                except KeyError:
                    self.raise_error('SyntaxError', 'undefined operation "' + op_name + '"', op)
                    return

        # run function
        try:
            # put argument in the mem
            if op['args_str'] != '':
                args = op['args_str']
                code = '(' + args + ')'
                # replace variable names with value of them
                for k in self.all_vars():
                    code = code.replace('$' + k, 'self.get_var("' + k + '")')
                    for used_namespace in self.used_namespaces:
                        if k[:len(used_namespace)+1] == used_namespace + '.':
                            tmp = k[len(used_namespace)+1:]
                            code = code.replace('$' + tmp, 'self.get_var("' + k + '")')

                self.mem = eval(code)
            else:
                self.mem = ''

            # execute function body
            self.exec_func(func_body)
            return
        except Exception as ex:
            self.raise_error('RuntimeError', str(ex), op)

    def signal_handler(self, signal, frame):
        ''' Raise error when signal exception raised '''
        self.raise_error('Signal', str(signal), self.operations[self.current_step])

    def start(self):
        ''' Start running the program '''

        signal.signal(signal.SIGINT, self.signal_handler)

        is_in_func = False
        self.current_step = 0

        # load the sections
        i = 0
        while i < len(self.operations):
            current_op = self.set_operation_index(self.operations[i])
            if current_op['command'] == 'section':
                if not is_in_func:
                    arg = current_op['args'][0]
                    self.sections[arg] = i+1
                    self.operations[i] = parser.parse('pass')[0]
            elif current_op['command'] == 'func':
                is_in_func = True
            elif current_op['command'] == 'endfunc':
                is_in_func = False
            i += 1

        self.current_step = 0
        while self.current_step < len(self.operations):
            try:
                self.run(self.operations[self.current_step])
            except Exception as ex:
                self.raise_error(
                    'RuntimeError',
                    str(ex),
                    self.set_operation_index(self.operations[self.current_step])
                )
            self.current_step += 1
