# Pota interpreter
To learn more about Pota programming language check out the [wiki](https://delfad0r.github.io/pota-wiki/).

## Setup
### Anywhere
The Pota interpreter is written in Python, so it should be supported by virtually every platform (but make sure you have Python 3.x installed).

To install the Pota interpreter download the repository somewhere (either via `git clone https://github.com/Delfad0r/pota.git` or via the [button](https://github.com/Delfad0r/pota/archive/master.zip) kindly provided by GitHub).  
Then, inside the `pota` directory, run `./setup.py install` (`sudo` may be required).

That's all there is to it. Now you should (hopefully) be able to run `pota -c '"Hello Pota!"o;'` and get back a cheerful `Hello Pota!`.

### Arch Linux
Thanks to [dariost](https://github.com/dariost) the Pota interpreter is hosted on the Arch User Repository (AUR).  
To install the package simply run `yaourt -S pota-git`.

## Running
To execute a Pota program simply type `pota myprogram.pota`.

Running `pota -h` produces the complete list of options supported by the interpreter.
