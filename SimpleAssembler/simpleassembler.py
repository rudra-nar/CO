import sys
import re

# Register mapping for RISC-V
register_map = {
    "zero": 0, "ra": 1, "sp": 2, "gp": 3, "tp": 4,
    "t0": 5, "t1": 6, "t2": 7, "s0": 8, "s1": 9,
    "a0": 10, "a1": 11, "a2": 12, "a3": 13, "a4": 14,
    "a5": 15, "a6": 16, "a7": 17, "s2": 18, "s3": 19,
    "s4": 20, "s5": 21, "s6": 22, "s7": 23, "s8": 24,
    "s9": 25, "s10": 26, "s11": 27, "t3": 28, "t4": 29,
    "t5": 30, "t6": 31
}

# Opcode, funct3, and funct7 mappings for R-type instructions
r_type_instructions = {
    "add": ("0110011", "000", "0000000"),
    "sub": ("0110011", "000", "0100000"),
    "slt": ("0110011", "010", "0000000"),
    "srl": ("0110011", "101", "0000000"),
    "or": ("0110011", "110", "0000000"),
    "and": ("0110011", "111", "0000000")
}

i_type_instructions = {
    "lw": ("0000011", "010"),
    "addi": ("0010011", "000"),
    "jalr": ("1100111", "000")
}

s_type_instructions = {
    "sw": ("0100011", "010")
}

b_type_instructions = {
    "beq": ("1100011", "000"),
    "bne": ("1100011", "001"),
    "blt": ("1100011", "100"),
}


j_type_instructions = {
    "jal": ("1101111")
}


def decimal_to_12bit_twos_complement(decimal_number):
    if decimal_number >= 0:
        binary_number = decimal_number
    else:
        binary_number = (1 << 12) + decimal_number
    return binary_number


#only for b type instructions
def decimal_to_13bit_twos_complement(decimal_number):
    if decimal_number >= 0:
        binary_number = decimal_number
    else:
        binary_number = (1 << 13) + decimal_number
    return binary_number

def convert_label_to_immediate(label, symbol_table, pc):
#used to convert label to an immediate which can be used later.
    if label not in symbol_table:
        raise ValueError(f"Undefined label: {label}")
    return symbol_table[label] - pc

def decimal_to_21bit_twos_complement(decimal_number):
    if decimal_number >= 0:
        binary_number = decimal_number
    else:
        binary_number = (1 << 21) + decimal_number
    return binary_number


def encode_r_type(opcode, funct3, funct7, rd, rs1, rs2, registers):
    """
    Encodes an R-type instruction into a 32-bit binary string.
    Checks for register overflow and arithmetic overflow.
    """
    if not (0 <= rd < 32 and 0 <= rs1 < 32 and 0 <= rs2 < 32):
        raise ValueError("Register index out of range (0-31)")
    
    # Check for overflow in arithmetic and shift operations
    if opcode == "0110011":
        if funct3 == "000":  # ADD or SUB instruction
            if funct7 == "0000000":  # ADD
                result = registers[rs1] + registers[rs2]
            elif funct7 == "0100000":  # SUB
                result = registers[rs1] - registers[rs2]
            else:
                result = 0  # Default case (should not happen)
            if result > (2**31 - 1) or result < -(2**31):
                raise OverflowError("Arithmetic overflow detected in ADD/SUB instruction")
        elif funct3 in ["001", "101"]:  # SLL, SRL, or SRA instruction
            shift_amount = registers[rs2] & 0x1F  # Only lower 5 bits are used
            if funct3 == "001":  # SLL
                result = registers[rs1] << shift_amount
            elif funct3 == "101":
                if funct7 == "0000000":  # SRL
                    result = registers[rs1] >> shift_amount
                elif funct7 == "0100000":  # SRA (Arithmetic shift right)
                    result = (registers[rs1] >> shift_amount) if registers[rs1] >= 0 else ((registers[rs1] + 0x100000000) >> shift_amount)
            if result > (2**31 - 1) or result < -(2**31):
                raise OverflowError("Shift operation overflow detected in SLL/SRL/SRA instruction")
    
    return f"{funct7}{rs2:05b}{rs1:05b}{funct3}{rd:05b}{opcode}"

def encode_i_type(opcode, funct3, rd, rs1, immediate, registers):
    if not (0 <= rd < 32 and 0 <= rs1 < 32):
        raise ValueError("Register index out of range (0-31)")
    if (opcode == "0000011"):
        imm = decimal_to_12bit_twos_complement(immediate)
        if (immediate > (2**11-1) or immediate < -(2**11)):
            raise ValueError("Value of Immediate out of range")
        return f"{imm:012b}{rs1:05b}{funct3}{rd:05b}{opcode}"
    elif (opcode == "0010011"):
        result = registers[rs1] + immediate #addition with immediate
        imm = decimal_to_12bit_twos_complement(immediate)
        if result > (2**31 - 1) or result < -(2**31) or immediate > (2**11-1) or immediate < -(2**11):
            raise OverflowError("Arithmetic overflow detected in ADD/SUB instruction")
        return f"{imm:012b}{rs1:05b}{funct3}{rd:05b}{opcode}"
    elif (opcode == "1100111"):
        #idk do something here 
        # jalr type instruction will be done later
        imm = decimal_to_12bit_twos_complement(immediate)
        target_address = (registers[rs1] + immediate) & ~1
        if target_address % 4 != 0:
            raise ValueError("JALR target address must be word-aligned")
        return f"{imm:012b}{rs1:05b}{funct3}{rd:05b}{opcode}"

def encode_s_type(opcode, funct3, rs1, rs2, immediate, registers):
    if not (0 <= rs1 < 32 and 0 <= rs2 < 32):
        raise ValueError("Register index out of range (0-31)")
    if (opcode == "0100011"):
        imm = decimal_to_12bit_twos_complement(immediate)
        if (immediate > (2**11-1) or immediate < -(2**11)):
            raise ValueError("Value of Immediate out of range")
        imm = str(f"{imm:012b}")
        imm7 = imm[0:7]
        imm5 = imm[7:12]
    return f"{imm7}{rs2:05b}{rs1:05b}{funct3}{imm5}{opcode}"


def encode_b_type(opcode, funct3, rs1, rs2, immediate, registers):
    if not (0 <= rs1 < 32 and 0 <= rs2 < 32):
        raise ValueError("Register index out of range (0-31)")

    # Check if immediate is within the valid signed 13-bit range (-4096 to 4095)
    if immediate > (2**12 - 1) or immediate < -(2**12):
        raise ValueError("Immediate value out of range (-4096 to 4095)")

    # Convert immediate to 13-bit two’s complement
    imm = decimal_to_13bit_twos_complement(immediate)
    imm_bin = f"{imm:013b}"  # Convert to a 13-bit binary string

    # RISC-V B-type immediate field breakdown:
    imm12 = imm_bin[0]      # Bit 12
    imm10_5 = imm_bin[1:7]  # Bits 10-5
    imm4_1 = imm_bin[7:11]  # Bits 4-1
    imm11 = imm_bin[11]     # Bit 11

    return f"{imm12}{imm10_5}{rs2:05b}{rs1:05b}{funct3}{imm4_1}{imm11}{opcode}"
    

def encode_j_type(opcode, rd, immediate, registers):
    if not (0 <= rd < 32):
        raise ValueError("Register index out of range (0-31)")

    # Ensure immediate fits in signed 21-bit range (-1048576 to 1048575)
    if immediate > (2**20 - 1) or immediate < -(2**20):
        raise ValueError("Immediate value out of range (-1048576 to 1048575)")

    # Convert to 21-bit two's complement
    imm = decimal_to_21bit_twos_complement(immediate)
    imm_bin = f"{imm:021b}"  # Convert to a 21-bit binary string

    # Extract immediate parts according to J-type encoding
    imm20 = imm_bin[0]        # Bit 20
    imm10_1 = imm_bin[10:20]  # Bits 10-1
    imm11 = imm_bin[9]        # Bit 11
    imm19_12 = imm_bin[1:9]   # Bits 19-12

    return f"{imm20}{imm19_12}{imm11}{imm10_1}{rd:05b}{opcode}"


def parse_instruction(line, symbol_table, pc, registers):
    pc+=4
    """
    Parses a single line of assembly code and converts it into binary.
    """
    tokens = re.split(r'[;,:.\s]+', line)
    print(tokens, pc)
    if not tokens:
        return None  # Ignore empty lines
    

    if(tokens[0] not in r_type_instructions and tokens[0] not in i_type_instructions and tokens[0] not in j_type_instructions and tokens[0] not in b_type_instructions and tokens[0] not in s_type_instructions):
        tokens.pop(0)
    
    instruction = tokens[0]
    if instruction in r_type_instructions:
        opcode, funct3, funct7 = r_type_instructions[instruction]
        try:
            rd = register_map.get(tokens[1], None)
            rs1 = register_map.get(tokens[2], None)
            rs2 = register_map.get(tokens[3], None)
            
            if rd is None or rs1 is None or rs2 is None:
                raise ValueError("Invalid register name")
            
            return encode_r_type(opcode, funct3, funct7, rd, rs1, rs2, registers),pc
        except (ValueError, IndexError):
            raise ValueError("Invalid R-type instruction format or register index out of range")
    elif instruction in i_type_instructions:
        opcode, funct3 = i_type_instructions[instruction]
        if (instruction == "addi" or instruction == "jalr"):
            try:
                rd = register_map.get(tokens[1], None)
                rs1 = register_map.get(tokens[2], None)
                immediate = int(tokens[3])
                if rd is None or rs1 is None:
                    raise ValueError("Invalid register name")
                return encode_i_type(opcode, funct3, rd, rs1, immediate, registers),pc
            except (ValueError, IndexError):
                raise ValueError("Invalid I-type instruction format or register index out of range")
        elif (instruction == "lw"):
            try:
                rd = register_map.get(tokens[1], None)
                for i in range(len(tokens[2])):
                    if (tokens[2][i] == "("):
                        temp = i
                        break
                immediate = int(tokens[2][0:temp])
                rs1 = register_map.get(tokens[2][temp+1:-1:], None)
                if rd is None or rs1 is None:
                    raise ValueError("Invalid register name")
                return encode_i_type(opcode, funct3, rd, rs1, immediate, registers),pc
            except (ValueError, IndexError):
                raise ValueError("Invalid I-type instruction format or register index out of range")
    elif instruction in s_type_instructions:
        opcode, funct3 = s_type_instructions[instruction]
        if (instruction == "sw"):
            try:
                rs2 = register_map.get(tokens[1], None)
                for i in range(len(tokens[2])):
                    if (tokens[2][i] == "("):
                        temp = i
                        break
                immediate = int(tokens[2][0:temp])
                rs1 = register_map.get(tokens[2][temp+1:-1:], None)
                if rs1 is None or rs2 is None:
                    raise ValueError("Invalid register name")
                return encode_s_type(opcode, funct3, rs1, rs2, immediate, registers),pc
            except (ValueError, IndexError):
                raise ValueError("Invalid S-type instruction format or register index out of range")
    elif instruction in b_type_instructions:
        opcode, funct3 = b_type_instructions[instruction]
        try:
            rs1 = register_map.get(tokens[1], None)
            rs2 = register_map.get(tokens[2], None)
            if (tokens[3] in symbol_table):
                pc = symbol_table[tokens[3]]
                immediate = pc
            elif (tokens[3].isnumeric() or (number.isnumeric() and tokens[3][0] == '-')):
                immediate = int(tokens[3])
            else:
                raise ValueError("Invalid label name")
            if rs1 is None or rs2 is None:
                raise ValueError("Invalid register name")
            return encode_b_type(opcode, funct3, rs1, rs2, immediate, registers),pc
        except (ValueError, IndexError):
            raise ValueError("Invalid B-type instruction format or register index out of range")
    elif instruction in j_type_instructions:
        opcode = j_type_instructions[instruction]
        try:
            rd = register_map.get(tokens[1], None)
            number = tokens[2][1:]
            if (tokens[2] in symbol_table):
                pc = symbol_table[tokens[2]]
                immediate = pc
            elif (tokens[2].isnumeric() or (number.isnumeric() and tokens[2][0] == '-')):
                immediate = int(tokens[2])
            else:
                raise ValueError("Invalid label name")
            if rd is None:
                raise ValueError("Invalid register name")
            return encode_j_type(opcode, rd, immediate, registers),pc
        except (ValueError, IndexError):
            raise ValueError("Invalid J-type instruction format or register index out of range")
    return None  # Placeholder


def first_pass(lines):
    """
    First pass: Collect labels and their corresponding addresses.
    """
    symbol_table = {}
    pc = 0
    for line in lines:
        tokens = re.split(r'[;,.\s]+', line)
        if(tokens and ':' in tokens[0]):
            for i in range(len(tokens[0])):
                if (tokens[0][i] == ':'):
                    break
            label = tokens[0][:i]
            symbol_table[label] = pc
            pc+=4
        else:
            pc += 4  # Each instruction is 4 bytes
    # print(symbol_table)
    return symbol_table

def assemble(input,output):

    """
    Reads an assembly file, converts it into binary, and writes the output.
    """
    with open(input, 'r') as f:
        lines = [line.strip() for line in f.readlines()]
    

    symbol_table = first_pass(lines)
    registers = [0] * 32  # Initialize 32 registers with 0
    
    binary_instructions = []
    pc = 0
    for line in lines:
        try:
            binary_instruction,pc = parse_instruction(line, symbol_table, pc, registers)
            if binary_instruction:
                print(binary_instruction)
                binary_instructions.append(binary_instruction)
        except (ValueError, OverflowError) as e:
            print(f"Error at PC {pc}: {e}")
            return
    
    with open(output, 'w') as f:
        for binary in binary_instructions:
            f.write(binary + '\n')


if len(sys.argv) != 3:
    print("Usage: python assembler.py <input_file> <output_file>")
    sys.exit(1)

input_file = sys.argv[1]  # Get input filename from command line
output_file = sys.argv[2]  # Get output filename from command line

assemble(input_file, output_file)  # Pass correct file paths'

