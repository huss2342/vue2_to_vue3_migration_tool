class Vue3Generator:
    def __init__(self, component):
        self.component = component
        self.indent = "    "

    def generate(self):
        imports = self._generate_imports()
        components = self._generate_components()
        props = self._generate_props()
        setup = self._generate_setup()

        component_content = f"{self.indent}name: '{self.component.name}'"
        if components:
            component_content += f",\n{components}"

        if props:
            component_content += f",\n{self.indent}props: {{\n{props}\n{self.indent}}}"

        if self.component.has_setup_content:
            component_content += f",\n{self.indent}setup() {{\n{setup}\n{self.indent}}}"

        return f"""<script>
{imports}

export default defineComponent({{
{component_content}
}});
</script>"""

    def _generate_imports(self):
        imports = []
        vue_imports = ["defineComponent"]

        if self.component.computed:
            vue_imports.append('computed')

        imports.append(f"import {{ {', '.join(sorted(vue_imports))} }} from 'vue';")

        if self.component.uses_vuex:
            imports.append("import { useStore } from 'js/store';")

        for import_statement in self.component.imports:
            if 'vuex' not in import_statement and 'mapGetters' not in import_statement:
                imports.append(import_statement+';')

        return "\n".join(imports)

    def _generate_components(self):
        if not self.component.components:
            return ""
        components = [f"{self.indent}{self.indent}{comp}" for comp in self.component.components.keys()]
        return f"{self.indent}components: {{\n{',\\n'.join(components)}\n{self.indent}}}"

    def _generate_props(self):
        if not self.component.props:
            return ""
        prop_strings = []
        for prop, value in self.component.props.items():
            prop_string = f"{self.indent}{self.indent}{prop}: {value}"
            prop_strings.append(prop_string)
        return ',\n'.join(prop_strings)

    def _generate_setup(self):
        setup_content = []

        if self.component.uses_vuex:
            setup_content.append(f"{self.indent}{self.indent}const store = useStore();")

        for name, body in self.component.computed.items():
            setup_content.append(f"{self.indent}{self.indent}const {name} = computed(() => {body});")

        for name, (params, body) in self.component.methods.items():
            body = body.strip()
            params = params.strip()

            # Handle parentheses for parameters
            if ',' in params or not params:
                params = f"({params})"

            if body.count(';') > 1:
                # Multi-statement method
                setup_content.append(f"{self.indent}{self.indent}const {name} = {params} => {{{body}}};")
            else:
                # Single-statement method
                body = body.strip(';')  # Remove trailing semicolon if present
                if body.startswith("return "):
                    body = body[
                           len("return "):]
                setup_content.append(f"{self.indent}{self.indent}const {name} = {params} => {body};")

        return_statement = f"{self.indent}{self.indent}return {{"
        return_items = list(self.component.computed.keys()) + list(self.component.methods.keys())
        return_statement += f"\n{self.indent}{self.indent}{self.indent}" + f",\n{self.indent}{self.indent}{self.indent}".join(
            return_items)
        return_statement += f"\n{self.indent}{self.indent}}};"

        setup_content.append(return_statement)

        return "\n".join(setup_content)