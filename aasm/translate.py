from argparse import ArgumentParser
from datetime import datetime
from typing import List, Tuple

from aasm.generating.spade import get_spade_code


def get_args() -> Tuple[str, str, bool]:
    parser = ArgumentParser()
    parser.add_argument('input_path', type=str, help='path to the input file')
    parser.add_argument('-d', '--debug', action='store_true', help='toggle the compiler debug mode')
    parser.add_argument('-o', '--output-path', type=str, default='out', help='the output file path')
    args = parser.parse_args()
    return args.input_path, args.output_path, args.debug


def get_input(input_path: str) -> List[str]:
    with open(input_path, 'r') as f:
        lines = f.readlines()
    return lines


def save_output(output_path: str, code: List[str]) -> None:
    with open(output_path, 'w') as f:
        for code_line in code:
            f.write(code_line)


def main(input_path: str, output_path: str, debug: bool) -> None:
    lines = get_input(input_path)
    start_time = datetime.now()
    spade_code = get_spade_code(lines, debug)
    time_delta = (datetime.now() - start_time).total_seconds()
    save_output(output_path, spade_code)
    print(f'({time_delta}s) Your results are saved in the file "{output_path}" 😎')


if __name__ == '__main__':
    input_path, output_path, debug = get_args()
    main(input_path, output_path, debug)
