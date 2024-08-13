from myAST import Vue2Scanner
from generator import Vue3Generator
# import jsbeautifier

def read_file(file_path):
    with open(file_path, 'r') as file:
        return file.read()


def write_file(file_path, content):
    with open(file_path, 'w') as file:
        file.write(content)


def convert_vue2_to_vue3(content):
    print("DEBUG: Starting conversion process")

    scanner = Vue2Scanner(content)
    component = scanner.scan()

    print("\nDEBUG: Scanned component details:")
    print(f"Name: {component.name}")
    print(f"Props: {component.props}")
    print(f"Computed: {component.computed}")
    print(f"Methods: {component.methods}")
    print(f"Watch: {component.watch}")
    print(f"Lifecycle hooks: {component.lifecycle_hooks}")
    print(f"Uses Vuex: {component.uses_vuex}")
    print(f"Imports: {component.imports}")
    print(f"Components: {component.components}")
    print(f"Data: {component.data}")

    generator = Vue3Generator(component)
    converted = generator.generate()

    print("\nDEBUG: Generated content:")
    print(converted)

    return converted


def main():
    input_file = "input.txt"
    output_file = "output.txt"

    print(f"DEBUG: Reading input from {input_file}")
    content = read_file(input_file)

    converted_content = convert_vue2_to_vue3(content)
    # converted_content = jsbeautifier.beautify(converted_content)

    print(f"\nDEBUG: Writing output to {output_file}")
    write_file(output_file, converted_content)

    print(f"Conversion complete. Output written to {output_file}")


if __name__ == "__main__":
    main()