#!/usr/bin/env python3

# Pota interpreter - https://github.com/Delfad0r/pota
# Copyright © 2016 Filippo Baroni <filippo.gianni.baroni@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from collections import defaultdict, deque
import itertools
import random
import time
import sys


DIRECTIONS = {
    '<' : (-1, 0),
    '>' : (1, 0),
    '^' : (0, -1),
    'v' : (0, 1)
}

MIRRORS = { 
    '/'  : lambda x, y: (-y, -x),
    '\\' : lambda x, y: (y, x),
    '|'  : lambda x, y: (-x, y),
    '_'  : lambda x, y: (x, -y),
    'x'  : lambda x, y: random.choice(list(DIRECTIONS.values()))
}

STACKMANIP = {
    # Arith
    '+' : (2, lambda x, y: [int(y) + int(x)]),
    '-' : (2, lambda x, y: [int(y) - int(x)]),
    '*' : (2, lambda x, y: [int(y) * int(x)]),
    '%' : (2, lambda x, y: [int(y) // int(x), int(y) % int(x)]),
    # Concat
    '.' : (2, lambda x, y: [str(y) + str(x)]),
    # Cmp
    '=' : (2, lambda x, y: ['1' if str(y) == str(x) else '0']),
    '(' : (2, lambda x, y: ['1' if str(y) < str(x) else '0']),
    ')' : (2, lambda x, y: ['1' if str(y) > str(x) else '0']),
    '[' : (2, lambda x, y: ['1' if int(y) < int(x) else '0']),
    ']' : (2, lambda x, y: ['1' if int(y) > int(x) else '0']),
    # Duplicate
    ',' : (1, lambda x: [x, x]),
    # Pop
    '~' : (1, lambda x: []),
    # Swap
    '$' : (2, lambda x, y: [x, y]),
    # Chr
    'c' : (1, lambda x: [chr(int(x))]),
    # Ord
    'a' : (1, lambda x: [ord(str(x))])
}


class PotaError(Exception):
    pass


class Code:
    
    def __init__(self, string):
        lines = string.splitlines()
        #shebang
        if lines[0][: 2] == '#!':
            lines.pop(0)
        self.code = {}
        self.maxw = defaultdict(int)
        self.maxh = defaultdict(int)
        self.rows = defaultdict(set)
        self.cols = defaultdict(set)
        for y in range(len(lines)):
            for x in range(len(lines[y])):
                self.set(x, y, lines[y][x])
    
    def get(self, x, y):
        return self.code.get((x, y), ' ')
    
    def set(self, x, y, v):
        if v == ' ':
            if (x, y) in self.code:
                del self.code[(x, y)]
                del self.rows[y][x]
                if self.maxw[y] == x:
                    self.maxw[y] = max(0, 0, *self.rows[y])
                del self.cols[x][y]
                if self.maxh[x] == y:
                    self.maxh[x] = max(0, 0, *self.cols[x])
        else:
            self.code[(x, y)] = v
            self.rows[y].add(x)
            self.cols[x].add(y)
            if self.maxw[y] < x:
                self.maxw[y] = x
            if self.maxh[x] < y:
                self.maxh[x] = y
    
    def get_maxw(self, y):
        return self.maxw.get(y, 0)
    
    def get_maxh(self, x):
        return self.maxh.get(x, 0)


class Pointer:
    
    def __init__(self, stack = [], direction = DIRECTIONS['>'], x = 0, y = 0):
        global ptrs_freeidx
        self.idx = ptrs_freeidx
        ptrs_freeidx += 1
        self.direction = direction
        self.stringmode = None
        self.x, self.y = x, y
        self.stacks = [deque(stack)]
        self.alive = True
        self.must_skip = False
        self.messages = deque()
        self.instructions = deque(code.get(self.x, self.y))
    
    def move(self):
        if self.instructions:
            instr = self.instructions.popleft()
            try:
                self.exec_instruction(instr)
            except IndexError:
                raise PotaError('Tried to pop from empty stack')
            except ZeroDivisionError:
                raise PotaError('Division by zero')
            except ValueError:
                raise PotaError('Cannot convert to integer')
            except TypeError:
                raise PotaError('Expected a single char')
        else:
            self.x += self.direction[0]
            self.y += self.direction[1]
            if self.direction[1] < 0 and self.y < 0:
                self.must_skip = False
                self.y = code.get_maxh(self.x)
            elif self.direction[1] > 0 and self.y > code.get_maxh(self.x):
                self.must_skip = False
                self.y = 0
            if self.direction[0] < 0 and self.x < 0:
                self.must_skip = False
                self.x = code.get_maxw(self.y)
            elif self.direction[0] > 0 and self.x > code.get_maxw(self.y):
                self.must_skip = False
                self.x = 0
            if debug.__contains__(self.idx):
                print('[# Pointer {:>2} moving to ({:>2}, {:>2})#]'
                      .format(self.idx, self.x, self.y, [list(s) for s in self.stacks]), file = sys.stderr)
            if self.must_skip:
                self.must_skip = False
            else:
                self.instructions.extend(code.get(self.x, self.y))
        return self.alive and (not self.instructions or self.instructions[0] != '#')
    
    def exec_instruction(self, instr):
        # skip
        if self.must_skip:
            self.must_skip = False
            return
        # string mode
        elif instr in '"\'' and self.stringmode is None:
            if debug.__contains__(self.idx):
                print('[# Pointer {:>2} in ({:>2}, {:>2}) entering string mode {} #]'
                      .format(self.idx, self.x, self.y, instr, [list(s) for s in self.stacks]), file = sys.stderr)
            self.stringmode = instr
            self.push('')
        elif instr == self.stringmode:
            if debug.__contains__(self.idx):
                print('[# Pointer {:>2} in ({:>2}, {:>2}) leaving string mode {} #]'
                      .format(self.idx, self.x, self.y, self.stringmode, [list(s) for s in self.stacks]), file = sys.stderr)
            self.stringmode = None
        elif self.stringmode:
            self.stacks[-1][-1] += instr
        # NOP
        elif instr == ' ':
            pass
        else:
            if debug.__contains__(self.idx):
                print('[# Pointer {:>2} in ({:>2}, {:>2}) executing \'{}\' with stacks {} #]'
                      .format(self.idx, self.x, self.y, instr, [list(s) for s in self.stacks]), file = sys.stderr)
            # Arrows
            if instr in DIRECTIONS:
                self.direction = DIRECTIONS[instr]
            # Mirrors
            elif instr in MIRRORS:
                self.direction = MIRRORS[instr](*self.direction)
            # Skip
            elif instr == '!':
                self.must_skip = True
            # CondSkip
            elif instr == '?':
                self.must_skip = str(self.pop()) != '0'
            # Where
            elif instr == 'w':
                self.push(self.x)
                self.push(self.y)
            # Jump
            elif instr == 'j':
                self.y, self.x = int(self.pop()), int(self.pop())
                if self.x < 0 or self.y < 0:
                    raise PotaError('Jump to negative position')
            # Digits
            elif instr in '0123456789':
                self.push(instr)
            # stack manipulation
            elif instr in STACKMANIP:
                (cnt, f) = STACKMANIP[instr]
                l = []
                for i in range(cnt):
                    l.append(self.pop())
                self.stacks[-1].extend(f(*l))
            # SConcat
            elif instr == ':':
                self.stacks[-1] = deque([''.join(map(str, self.stacks[-1]))])
            # Rotate
            elif instr == '{':
                self.stacks[-1].rotate(-1)
            elif instr == '}':
                self.stacks[-1].rotate(1)
            # Reverse
            elif instr == 'r':
                self.stacks[-1].reverse()
            # Explode
            elif instr == 'e':
                self.stacks.append(deque(str(self.pop())))
            # New
            elif instr == 'n':
                cnt = int(self.pop())
                new_stack = deque()
                for i in range(cnt):
                    new_stack.appendleft(self.pop())
                self.stacks.append(new_stack)
            # Merge
            elif instr == 'm':
                old_stack = self.stacks.pop()
                if len(self.stacks):
                    self.stacks[-1].extend(old_stack)
                else:
                    self.stacks = [deque()]
            # SDuplicate
            elif instr == 'd':
                self.stacks.append(deque(self.stacks[-1]))
            # Length
            elif instr == 'l':
                self.push(len(self.stacks[-1]))
            # Exec
            elif instr == '`':
                self.instructions.extendleft(reversed(str(self.pop())))
            # Get
            elif instr == 'g':
                y, x = int(self.pop()), int(self.pop())
                self.push(code.get(x, y))
            # Put
            elif instr == 'p':
                y, x, v = int(self.pop()), int(self.pop()), str(self.pop())
                code.set(x, y, v)
            # Spawn
            elif instr == '&':
                cnt = int(self.pop())
                new_stack = deque()
                for i in range(cnt):
                    new_stack.appendleft(self.pop())
                new_ptr = Pointer(stack = new_stack, direction = self.direction,
                    x = self.x + self.direction[0], y = self.y + self.direction[1])
                ptrs[new_ptr.idx] = new_ptr
            # Wait
            elif instr == '#':
                if len(self.messages):
                    self.push(self.messages.popleft())
                else:
                    self.instructions.appendleft('#')
            # Send
            elif instr == '@':
                at, v = int(self.pop()), self.pop()
                if at in ptrs:
                    ptrs[at].messages.append(v)
                else:
                    raise PotaError('Pointer {} does not exist'.format(at))
            # Id
            elif instr == 'y':
                self.push(self.idx)
            # In
            elif instr == 'i':
                if sys.stdin.isatty():
                    c = getch()
                    if ord(c) == 3:
                        self.output('^C\n')
                        raise KeyboardInterrupt
                    else:
                        self.push(c)
                else:
                    c = sys.stdin.read(1)
                    self.push(c)
            # Out
            elif instr == 'o':
                self.output(str(self.pop()))
            # Die
            elif instr == ';':
                self.alive = False
            # invalid instruction
            else:
                raise PotaError('Invalid instruction: ' + instr)
    
    def pop(self):
        return self.stacks[-1].pop()
    
    def push(self, x):
        self.stacks[-1].append(x)
    
    def output(self, s):
        sys.stdout.write(s)
        sys.stdout.flush()

# copy-pasted from the Internet
def _find_getch():
    try:
        import termios
    except ImportError:
        import msvcrt
        return msvcrt.getch

    import sys, tty
    def _getch():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

    return _getch

# read single character without waiting for '\n' 
getch = _find_getch()


def read_code(string):
    lines = string.splitlines()
    #shebang
    if lines[0][: 2] == '#!':
        lines.pop(0)
    code = defaultdict(dict)
    for y in range(len(lines)):
        for x in range(len(lines[y])):
            if lines[y][x] != ' ':
                code[y][x] = lines[y][x]
    return code


code = None
ptrs = None
ptrs_freeidx = None
ptrs_new = None
debug = None

def main():
    import argparse
    
    global code
    global ptrs
    global ptrs_freeidx
    global ptrs_new
    global debug
    
    parser = argparse.ArgumentParser(description = 'Pota interpreter',
    usage = '%(prog)s [-h] [<script> | -c <code>] [<options>]')
    code_group = parser.add_argument_group('code')
    code_group_mutex = code_group.add_mutually_exclusive_group(required = True)
    code_group_mutex.add_argument('script',
                            type = argparse.FileType('r'),
                            nargs = '?',
                            metavar = '<script>',
                            help = '.pota source file to execute')
    code_group_mutex.add_argument('-c', '--code',
                            metavar = '<code>',
                            help = 'string of Pota instructions to execute')
    options_group = parser.add_argument_group('options')
    options_group.add_argument('-s', '--stack',
                               nargs = '*',
                               dest = 'stack',
                               metavar = '<val>',
                               help = 'fill the stack before the execution starts')
    options_group.add_argument('-d', '--debug',
                               nargs = '*',
                               type = int,
                               default = None,
                               metavar = '<ptr>',
                               help = """enable debug mode for Pointers with id <ptr>;
                                         use "-d"/"--debug" to enable debug mode for all pointers""")
    options_group.add_argument('-t', '--tick',
                               type = float,
                               default = None,
                               metavar = '<tick>',
                               help = """wait at least <tick> seconds between instructions;
                                         if <tick> is a negative number, then wait for the user
                                         to press <Enter> before executing the next instruction""")                               
    args = parser.parse_args()
    
    if args.script:
        codestr = args.script.read()
        args.script.close()
    else:
        codestr = args.code
    code = Code(codestr)
    if not args.stack:
        args.stack = []
    if args.debug is None:
        debug = lambda: None
        debug.__contains__ = lambda item: False
    elif args.debug == []:
        debug = lambda: None
        debug.__contains__ = lambda item: True
    else:
        debug = set(args.debug)
    
    ptrs_freeidx = 0
    ptrs = {}
    ptrs[0] = Pointer(stack = args.stack)
    try:
        while ptrs:
            for i, p in list(ptrs.items()):
                if args.tick is None:
                    while p.move():
                        pass
                    if not p.alive:
                        del ptrs[i]
                else:
                    begin_time = time.clock()
                    p.move()
                    if not p.alive:
                        del ptrs[i]
                    if args.tick >= 0:
                        if time.clock() - begin_time < args.tick:
                            time.sleep(args.tick - (time.clock() - begin_time))
                    else:
                        input()
    except PotaError as e:
        print('Pota! ' + str(e))
        exit(0)
    except KeyboardInterrupt:
        exit(0)
    print()


if __name__ == '__main__':
    main()
