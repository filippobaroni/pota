#!/usr/bin/env python3

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
    '+' : (2, lambda x, y: [str(int(y) + int(x))]),
    '-' : (2, lambda x, y: [str(int(y) - int(x))]),
    '*' : (2, lambda x, y: [str(int(y) * int(x))]),
    '%' : (2, lambda x, y: [str(int(y) // int(x)), str(int(y) % int(x))]),
    # Concat
    '.' : (2, lambda x, y: [y + x]),
    # Cmp
    '=' : (2, lambda x, y: ['1' if y == x else '0']),
    '(' : (2, lambda x, y: ['1' if y < x else '0']),
    ')' : (2, lambda x, y: ['1' if y > x else '0']),
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
    'a' : (1, lambda x: [str(ord(x))])
}


class PotaError(Exception):
    pass


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
        self.instructions = deque(code.get(self.y, {}).get(self.x, ' '))
    
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
                self.y = max(itertools.chain(code.keys(), [0]))
            elif self.direction[1] > 0 and self.y > max(itertools.chain(code.keys(), [0])):
                self.must_skip = False
                self.y = 0
            if self.direction[0] < 0 and self.x < 0:
                self.must_skip = False
                self.x = max(itertools.chain(code[self.y].keys(), [0]))
            elif self.direction[0] > 0 and self.x > max(itertools.chain(code[self.y].keys(), [0])):
                self.must_skip = False
                self.x = 0
            if debug.__contains__(self.idx):
                print('[# Pointer {:>2} moving to ({:>2}, {:>2})#]'
                      .format(self.idx, self.x, self.y, [list(s) for s in self.stacks]), file = sys.stderr)
            if self.must_skip:
                self.must_skip = False
            else:
                self.instructions.extend(code.get(self.y, {}).get(self.x, ' '))
    
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
        # do nothing
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
                self.must_skip = self.pop() != '0'
            # Where
            elif instr == 'w':
                self.push(str(self.x))
                self.push(str(self.y))
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
                self.stacks[-1] = deque([''.join(self.stacks[-1])])
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
                self.stacks.append(deque(self.pop()))
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
                self.push(str(len(self.stacks[-1])))
            # Exec
            elif instr == '`':
                self.instructions.extendleft(reversed(self.pop()))
            # Get
            elif instr == 'g':
                y, x = int(self.pop()), int(self.pop())
                self.push(code.get(y, {}).get(x, ' '))
            # Put
            elif instr == 'p':
                y, x, v = int(self.pop()), int(self.pop()), self.pop()
                code[y][x] = v
                if v == ' ':
                    del code[y][x]
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
                self.push(str(self.idx))
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
                self.output(self.pop())
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

#read single character without waiting for '\n' 
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

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    code_group = parser.add_mutually_exclusive_group(required = True)
    code_group.add_argument('script',
                            type = argparse.FileType('r'),
                            nargs = '?')
    code_group.add_argument('-c', '--code')
    options_group = code_group.add_argument_group('options')
    options_group.add_argument('-s', '--stack',
                               nargs = '*',
                               dest = 'stack')
    options_group.add_argument('-d', '--debug',
                               nargs = '*',
                               type = int,
                               default = None)
    options_group.add_argument('-t', '--tick',
                               type = float,
                               default = None)
    args = parser.parse_args()
    
    if args.script:
        codestr = args.script.read()
        args.script.close()
    else:
        codestr = args.code
    code = read_code(codestr)
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
            if args.tick is not None:
                begin_time = time.clock()
            for i, p in list(ptrs.items()):
                p.move()
                if not p.alive:
                    del ptrs[i]
            if args.tick is not None:
                if args.tick > 0:
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

