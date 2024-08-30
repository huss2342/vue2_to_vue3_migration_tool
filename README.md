# Vue2 to Vue3 Migration Tool

## Overview
This tool is designed to assist in the migration process from Vue2 to Vue3 by automatically converting Vue2 component syntax to Vue3 composition API syntax. It aims to speed up the migration process by handling many of the repetitive conversion tasks.

## Current State
This tool is currently a work in progress. While it can handle many common conversion scenarios, it may not cover all edge cases and might occasionally produce output that requires manual adjustment.

## Features
- Converts Vue2 component syntax to Vue3 composition API syntax
- Handles conversion of data, computed properties, methods, and lifecycle hooks
- Manages imports and Vuex integration
- Preserves existing logic while updating to Vue3 patterns

## Limitations
- Does not add the `<script setup>` tag; uses the standard `<script>` tag instead
- Retains the `return` statement in the `setup` function rather than using top-level variables
- Will miss semicolons or make other minor syntax errors
- Complex or nested structures might require manual review and adjustment
- It will have issues with lines that use regex
- Review the input.txt and output.txt files for current limitation

## Usage
1. Place your Vue2 component code in the `input.txt` file.
2. Run the main script:
   ```
   python main.py
   ```
3. The converted Vue3 code will be output to `output.txt`.
4. Review the output and make any necessary manual adjustments.

## Project Structure
- `main.py`: The entry point of the application
- `parser.py`: Contains the `Vue2Scanner` class for parsing Vue2 components
- `generator.py`: Contains the `Vue3Generator` class for generating Vue3 syntax
- `Vue2Component.py`: Defines the structure for storing component information

## Contributing
As this is a work in progress, contributions are welcome! If you encounter any issues or have suggestions for improvements, please feel free to open an issue or submit a pull request.

## Disclaimer
This tool is meant to assist in the migration process and should not be relied upon for fully automatic, error-free conversions. Always review and test the output thoroughly before using it in a production environment.

## License
This project is open source and free to use. Anyone can use, modify, and distribute this code without any restrictions. No attribution is required.

---

Remember to thoroughly test the converted components and refer to the official Vue 3 migration guide for best practices and manual adjustments that may be necessary.
