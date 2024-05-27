
# Compiler

This project is a compiler for a simple imperative programming language. The compiler translates source code written in this language into bytecode for a specified virtual machine. The generated bytecode is optimized for execution speed and size, particularly for multiplication and division operations, which are designed to run in logarithmic time relative to the values of the arguments. Developed as a final project for Formal Languages and Translations Techniques course at Wrocław University of Science and Technology held by prof. Maciej Gębala [https://cs.pwr.edu.pl/gebala/](Url).




## Language Specification

The language has the following features and rules:

- **Arithmetic Operations**: Operations are performed on natural numbers. Subtracting a larger number from a smaller one results in 0. Division by zero results in both the quotient and remainder being 0.
- **Array Declarations**: t[100] declares an array with 100 elements indexed from 0 to 99.
- Procedures:
    - **Recursion**: Procedures cannot be recursive.
    - **Parameters**: Parameters are passed by reference (IN-OUT).
    - **Variable Scope**: Variables used within a procedure must be either formal parameters or declared inside the procedure.
    - **Array Parameters**: Array parameters must be preceded by the letter T.
    - **Procedure Calls**: Procedures can only call previously defined procedures. Actual parameters can be both formal parameters of the calling procedure and its local variables.
- **REPEAT-UNTIL Loop**: The loop executes at least once and continues until the condition specified after UNTIL is met.
- **READ/WRITE Instructions**: READ reads a value from the input and assigns it to a variable, and WRITE outputs the value of a variable or a number.
- **Other Instructions**: Standard imperative language instructions with typical meanings.
- **Identifiers**: pidentifier follows the regular expression [_a-z]+.
- **Numerical Constants**: Natural numbers in decimal notation. Input constants are limited to 64-bit integers (long long), but the virtual machine supports arbitrary-sized natural numbers.

## Error Handling

The compiler should detect and report errors, including but not limited to:

- Redeclaration of variables
- Usage of undeclared variables
- Unknown procedure names


## Techologies Used

- Python 3.10.12
- sly 0.5

## Usage
 
Firstly, in the main directory run:

```bash
    python3 compiler/compiler.py <input.file> <output.file>
```

Secondly, in "maszyna_wirtualna" folder run:
```
    make
```
Lastly, run:
```
    ./maszyna_wirtualna/maszyna-wirtualna <output.file>
```

**Note**: Compilation is necessary before running the project.


## Files
- **compiler.py**: Contains the lexer and parser. Reads the input file and outputs code to the output file.
- **link.py**: Contains the Link class, which serves as a pointer for variables and arrays.
- **variable.py**: Contains the Variable class, which represents a variable in memory.
- **list.py**: Contains the List class, which represents an array in memory.
- **procedure.py**: Contains the Procedure class, which stores variables, lists, pointers, and constants.
- **program.py**: Contains the Program class, which stores procedures and generates assembly code for each procedure.
- **assembly_generator.py**: Contains methods for generating assembly code for the given procedure as input.
- **specification.pdf**: Contains a detailed description of the project in Polish.