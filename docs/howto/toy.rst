

Creating a toy language
=======================

In this how-to, we will develop our own toy language. We will use textx to
define our own language and use the ppci backend for optimization and code
generation.

As an example we will create a simple language that can calculate simple
expressions and use variables. An example of this toy language looks like
this:

.. code::

    b = 2;
    c = 5 + 5 * b;
    d = 133 * c - b;
    print b;
    print c;


The language is very limited (which makes it easy to implement), but it
contains enough for an example. The example above is stored in a file called
'example.tcf' (tcf stands for toy calculator format).

Part 0 - preparation
--------------------

Before we can begin creating the toy language compiler, we need the required
dependencies. For that a virtualenv can be created like this:

.. code:: bash

    [windel@hoefnix toydsl]$ virtualenv dslenv
    Using base prefix '/usr'
    New python executable in /home/windel/HG/ppci/examples/toydsl/dslenv/bin/python3
    Also creating executable in /home/windel/HG/ppci/examples/toydsl/dslenv/bin/python
    Installing setuptools, pip, wheel...done.
    [windel@hoefnix toydsl]$ source dslenv/bin/activate
    (dslenv) [windel@hoefnix toydsl]$ pip install textx ppci
    Collecting textx
    Collecting ppci
      Using cached ppci-0.5-py3-none-any.whl
    Collecting Arpeggio (from textx)
    Installing collected packages: Arpeggio, textx, ppci
    Successfully installed Arpeggio-1.5 ppci-0.5 textx-1.4
    (dslenv) [windel@hoefnix toydsl]$

After this step, we now have a virtual environment with textx and ppci
installed.

Part 1 - textx
--------------

In this part the parsing of the language will be done. A great deal will be
done by textx.
For a detailed
explanation of the workings of textx, please see:
http://igordejanovic.net/textX/

Lets define a grammar file, called toy.tx:

.. code::

    Program: statements*=Statement;
    Statement: (PrintStatement | AssignmentStatement) ';';
    PrintStatement: 'print' var=ID;
    AssignmentStatement: var=ID '=' expr=Expression;
    Expression: Sum;
    Sum: Product (('+'|'-') Product)*;
    Product: Value ('*' Value)*;
    Value: ID | INT | ('(' Expression ')');

This grammar is able to parse our toy language. Next we create a python
script to load this grammar and parse the toy example program:

.. code:: python

    from textx.metamodel import metamodel_from_file

    toy_mm = metamodel_from_file('toy.tx')

    # Load the program:
    program = toy_mm.model_from_file('example.tcf')

    for statement in program.statements:
        print(statement)

Now if we run this file, we see the following:

.. code:: bash

    (dslenv) [windel@hoefnix toydsl]$ python toy.py 
    <textx:AssignmentStatement object at 0x7f20c9d87cc0>
    <textx:AssignmentStatement object at 0x7f20c9d87908>
    <textx:AssignmentStatement object at 0x7f20c9d870b8>
    <textx:PrintStatement object at 0x7f20c9d87ac8>
    <textx:PrintStatement object at 0x7f20c9d95588>

We now have a simple parser for the toy language, and can parse it.

Part 2 - connecting the backend
-------------------------------

Now that we can parse the dsl, it is time to create new code from the parsed
format. To generate code, first the program must be translated to ir code.

The following snippet creates an IR-module, a procedure and a block to
store instructions in. Instructions at this point are not machine instructions
but abstract instructions that can be translated into any kind of machine
code later on.

.. code:: python

    from ppci import ir
    ir_module = ir.Module('toy')
    ir_function = ir.Procedure('toy', ir.Binding.GLOBAL)
    ir_module.add_function(ir_function)
    ir_block = ir.Block('entry')
    ir_function.entry = ir_block
    ir_function.add_block(ir_block)


Next, we need to translate each statement into some code, but we will do that
later.

.. code:: python

    for statement in program.statements:
        print(statement)

First we will add the closing code, that verifies our own constructed
module, and compiles the ir code to object code, links this and creates an
oj file.

.. code:: python

    ir_block.add_instruction(ir.Exit())

The code above creates an Exit instruction and adds the instruction to the
block. Next we can verify the IR-code, to make sure that the program we
created contains no errors. The ir_to_object function translates the program
from IR-code into an object for the given target architecture, in this case
x86_64, but you could as well use AVR or riscv here.

.. code:: python

    from ppci.irutils import Verifier
    from ppci import api
    Verifier().verify(ir_module)
    obj1 = api.ir_to_object([ir_module], 'x86_64')
    obj = api.link([obj1])
    print(obj)

The printed object shows that it conains 11 bytes.

.. code:: bash

    (dslenv) [windel@hoefnix toydsl]$ python toy.py
    ...
    CodeObject of 11 bytes
    (dslenv) [windel@hoefnix toydsl]$

We can write the object to file using the following code:

.. code:: python

    with open('example.oj', 'w') as f:
        obj.save(f)

The oj file is a ppci format for object files, pronounced 'ojee'. It is
a readable json format with the object information in it:

.. code:: json

    {
      "arch": "x86_64",
      "images": [],
      "relocations": [
        {
          "offset": "0x4",
          "section": "code",
          "symbol": "toy_toy_epilog",
          "type": "apply_b_jmp32"
        }
      ],
      "sections": [
        {
          "address": "0x0",
          "alignment": "0x4",
          "data": "",
          "name": "data"
        },
        {
          "address": "0x0",
          "alignment": "0x4",
          "data": "55488bece9000000005dc3",
          "name": "code"
        }
      ],
      "symbols": [
        {
          "name": "toy_toy",
          "section": "code",
          "value": "0x0"
        },
        {
          "name": "toy_toy_block_entry",
          "section": "code",
          "value": "0x4"
        },
        {
          "name": "toy_toy_epilog",
          "section": "code",
          "value": "0x9"
        }
      ]
    }

As you can see, there are two sections, for code and for data. The code
section contains some bytes. This is x86_64 machine code.

Part 3 - translating the elements
---------------------------------

In this part we will create code snippets for each type of TCF code. For this
we will use the textx context processor system, and we will also rewrite the
initial code such that we have a class that can translate TCF code into
IR-code. The entry point to the class will be a compile member function
that translates a TCF file into a IR-module.

The whole script now looks like this:

.. literalinclude:: ../../examples/toydsl/toy.py
    :language: python
    :linenos:


And the textx description is modified to include sum and product terms:

.. code::

    Program: statements*=Statement;
    Statement: (PrintStatement | AssignmentStatement) ';';
    PrintStatement: 'print' var=ID;
    AssignmentStatement: var=ID '=' expr=Expression;
    Expression: val=Sum;
    Sum: base=Product terms*=ExtraTerm;
    ExtraTerm: operator=Operator value=Product;
    Operator: '+' | '-';
    Product: base=Value factors*=ExtraFactor;
    ExtraFactor: operator='*' value=Value;
    Value: ID | INT | ('(' Expression ')');


When we run this script, the output is the following:

.. code:: bash

    (dslenv) [windel@hoefnix toydsl]$ python toy.py 
    CodeObject of 117 bytes
    (dslenv) [windel@hoefnix toydsl]$ 

As we can see, the object file has increased in size because we translated
the elements.

Part 4 - Creating a linux executable
------------------------------------

In this part we will create a linux executable from the object code we
created. We will do this very low level, without libc, directly using the
linux syscall api.

We will start with the low level assembly glue code (linux.asm):

.. code::

    section reset

    start:
        call toy_toy
        call bsp_exit

    bsp_syscall:
        mov rax, rdi ; abi param 1
        mov rdi, rsi ; abi param 2
        mov rsi, rdx ; abi param 3
        mov rdx, rcx ; abi param 4
        syscall
        ret

In this assembly snippet, we defined a sequence of code in the reset section
which calls our toy_toy function and next the bsp_exit function. Bsp is
an abbreviation for board support package, and we need it to connect other
code to the platform we run on. The syscall assembly function calls the linux
kernel with four parameters.

Next we define the rest of the bsp in bsp.c3:

.. code::

    module bsp;

    public function void putc(byte c)
    {
      syscall(1, 1, cast<int>(&c), 1);
    }

    function void exit()
    {
        syscall(60, 0, 0, 0);
    }

    function void syscall(int nr, int a, int b, int c);

Here we implement two syscalls, namely putc and exit.

For the print function, we will refer to the already existing io module
located in the librt folder of ppci. To compile and link the different parts
we use the following snippet:

.. code:: python

    obj1 = api.ir_to_object([ir_module], 'x86_64')
    obj2 = api.c3c(['bsp.c3', '../../librt/io.c3'], [], 'x86_64')
    obj3 = api.asm('linux.asm', 'x86_64')
    obj = api.link([obj1, obj2, obj3], layout='layout.mmap')

In this snippet, three object files are created. obj1 contains our toy
languaged compiled into x86 code. obj2 contains the c3 bsp and io code.
obj3 contains the assembly sourcecode.

For the link command we also use a layout file, telling the linker where
it must place which piece of the object file. In the case of linux, we use
the following (layout.mmap):

.. code::

    MEMORY code LOCATION=0x40000 SIZE=0x10000 {
        SECTION(reset)
        ALIGN(4)
        SECTION(code)
    }

    MEMORY ram LOCATION=0x20000000 SIZE=0xA000 {
        SECTION(data)
    }


As a final step, we invoke the objcopy command to create a linux ELF
executable:

.. code:: python

    # Create a linux elf file:
    api.objcopy(obj, 'code', 'elf', 'example')

This command creates a file called 'example', which is an ELF file for linux.
The file can be inspected with objdump:

.. code:: bash

    (dslenv) [windel@hoefnix toydsl]$ objdump example -d

    example:     file format elf64-x86-64


    Disassembly of section code:

    000000000004001c <toy_toy>:
       4001c:   55                      push   %rbp
       4001d:   41 56                   push   %r14
       4001f:   41 57                   push   %r15
       40021:   48 81 ec 18 00 00 00    sub    $0x18,%rsp
       40028:   48 8b ec                mov    %rsp,%rbp

    000000000004002b <toy_toy_block_entry>:
       4002b:   49 be 02 00 00 00 00    movabs $0x2,%r14
       40032:   00 00 00 
       40035:   4c 89 75 00             mov    %r14,0x0(%rbp)
       40039:   4c 8b 7d 00             mov    0x0(%rbp),%r15
       4003d:   49 be 05 00 00 00 00    movabs $0x5,%r14

    ...

We can now run the executable:

.. code::

    (dslenv) [windel@hoefnix toydsl]$ ./example
    Segmentation fault (core dumped)
    (dslenv) [windel@hoefnix toydsl]$

Sadly, this is not exactly what we hoped for!

The problem here is that we did not call the io_print function with the
proper arguments. To fix this, we can change the print handling routine
like this:

.. code:: python

    def handle_print(self, print_statement):
        self.logger.debug('print statement %s', print_statement.var)
        name = print_statement.var
        value = self.load_var(name)
        label_data = pack_string('{} :'.format(name))
        label = self.emit(ir.LiteralData(label_data, 'label'))
        self.emit(ir.ProcedureCall('io_print2', [label, value]))

We use here io_print2, which takes a label and a value. The label must be
packed as a pascal style string, meaning a length integer followed by
the string data. We can implement this string encoding with the following
function:

.. code:: python

    def pack_string(txt):
        ln = struct.pack('<Q', len(txt))
        return ln + txt.encode('ascii')

Now we can compile the TCF file again, and check the result:

.. code:: bash

    (dslenv) [windel@hoefnix toydsl]$ python toy.py
    CodeObject of 1049 bytes
    (dslenv) [windel@hoefnix toydsl]$ ./example
    b :0x00000002
    c :0x0000000F
    (dslenv) [windel@hoefnix toydsl]$ cat example.tcf
    b = 2;
    c = 5 + 5 * b;
    d = 133 * c - b;
    print b;
    print c;
    (dslenv) [windel@hoefnix toydsl]$

As we can see, the compiler worked out correctly!

Final words
-----------

In this tutorial we have seen how to create a simple language.
The entire example for this code can be found in the
examples/toydsl directory in the ppci repository at:
https://bitbucket.org/windel/ppci


