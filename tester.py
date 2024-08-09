def main():
    test_file_name = "test.txt"
    test_vue_file_name = "VariantContentSalesTab_VUE3.txt"
    input_file = "input.txt"
    output_file = "output.txt"

    # Read the contents of the files
    with open(input_file, 'r') as infile:
        input_content = infile.read()

    with open(output_file, 'r') as outfile:
        output_content = outfile.read()

    with open("EXAMPLES/"+test_vue_file_name, 'r') as vuefile:
        vue_content = vuefile.read()

    # Write to the test.txt file
    with open(test_file_name, 'w') as testfile:
        testfile.write("input file:\n")
        testfile.write("\n```\n")
        testfile.write(input_content)
        testfile.write("\n```\n\n")

        testfile.write("output file:\n")
        testfile.write("```\n")
        testfile.write(output_content)
        testfile.write("\n```\n\n")

        testfile.write("Expected output\n")
        testfile.write("```\n")
        testfile.write(vue_content)
        testfile.write("\n```\n")


if __name__ == "__main__":
    main()
