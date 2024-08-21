import re
import jsbeautifier


class Vue3Generator:
    def __init__(self, component):
        self.component = component
        self.indent = "    "

    def generate(self):
        imports = self._generate_imports()
        components = self._generate_components()
        mixins = self._generate_mixins()
        props = self._generate_props()
        setup = self._generate_setup()

        # Fixing syntax and making it look prettier
        setup = re.sub(r"this\.\$store", r'store', setup)
        setup = self.fix_this(setup)

        # Remove 'props' if it's used only once
        props_count = len(re.findall(r'\bprops\b', setup))
        if props_count == 1:
            setup = re.sub(r'\bprops\b', '', setup)

        # add root
        setup, imports = self.add_root_instance(setup, imports);
        setup, imports = self.fix_nextTick(setup, imports);

        # Beautify the setup function
        options = jsbeautifier.default_options()
        options.wrap_line_length = 149
        setup = jsbeautifier.beautify(setup, options)
        setup = re.sub(r'\)\s*$', ');', setup, flags=re.MULTILINE)
        setup = re.sub(r';;\s*$', ';', setup, flags=re.MULTILINE)
        setup = re.sub(r'return null;', 'return;', setup, flags=re.MULTILINE)

        # Generate component content
        component_content = [f"{self.indent}name: '{self.component.name}'"]

        if components:
            component_content.append(components)

        if mixins:
            component_content.append(mixins)

        if props:
            props_formatted = f"{self.indent}props: {{\n{props}\n{self.indent}}}"
            component_content.append(props_formatted)

        if setup:
            component_content.append(setup)

        # Join all parts of the component
        full_component = ',\n'.join(component_content)

        # Wrap the component in defineComponent
        script_content = f"""
<script>
{imports}

export default defineComponent({{
{full_component}
}});
</script>
"""

        return script_content.strip()

    def _generate_imports(self):
        imports = []
        vue_imports = ["defineComponent"]

        if self.component.computed:
            vue_imports.append('computed')

        if self.component.watch:
            vue_imports.append('watch')

        if self.component.data:
            vue_imports.append('ref')

        if self.component.lifecycle_hooks:
            if 'created' in self.component.lifecycle_hooks:
                vue_imports.append('onBeforeMount')
            if 'mounted' in self.component.lifecycle_hooks:
                vue_imports.append('onMounted')
            if 'beforeDestroy' in self.component.lifecycle_hooks:
                vue_imports.append('onBeforeUnmount')

        imports.append(f"import {{ {', '.join(sorted(vue_imports))} }} from 'vue'")

        if self.component.uses_vuex:
            imports.append("import { useStore } from 'js/store';")

        for import_statement in self.component.imports:
            if 'vuex' not in import_statement and 'mapGetters' not in import_statement:
                imports.append(import_statement + ";")
        return "\n".join(imports)

    def _generate_components(self):
        if not self.component.components:
            return ""

        components_content = f"{self.indent}components: {{\n"
        for name, value in self.component.components.items():
            # if it is the last component, remove the comma
            components_content += f"{self.indent * 2}{value},\n"
            if name == list(self.component.components.keys())[-1]:
                components_content = components_content[:-2] + "\n"
        components_content += f"{self.indent}}}"

        return components_content

    def _generate_mixins(self):
        if not self.component.mixins:
            return ""

        mixins_content = f"{self.indent}mixins: [{', '.join(self.component.mixins)}]"
        return mixins_content

    def _generate_props(self):
        if not self.component.props:
            return ""
        prop_strings = []
        for prop, value in self.component.props.items():
            prop_string = f"{self.indent}{self.indent}{prop}: {value}"

            # Remove single quotes around words using regex
            prop_string = re.sub(r"'(\w+)'", r'\1', prop_string)
            prop_string = re.sub(r"True", r'true', prop_string)
            prop_string = re.sub(r"False", r'false', prop_string)
            prop_string = re.sub(r"{(.*)}", r'{ \1 }', prop_string)
            prop_string = re.sub(r"\'\(\) \=\> \{\}'", r'() => {}', prop_string)
            prop_string = re.sub(r"\'\(\) \=\> \[\]'", r'() => {}', prop_string)
            prop_strings.append(prop_string)
        return ',\n'.join(prop_strings)

    def _generate_setup(self):
        # If there are no computed properties, methods, data, watch, or lifecycle hooks, return with no setup() method
        if not self.component.computed and not self.component.methods and not self.component.data \
                and not self.component.watch and not self.component.lifecycle_hooks:
            return ""

        setup_content = [f"{self.indent}setup(props) {{"]

        if self.component.uses_vuex:
            setup_content.append(f"{self.indent}{self.indent}const store = useStore();")
            setup_content.append('')

        setup_content.extend(self._generate_reactive_vars())

        setup_content.extend(self._generate_store_getters())

        setup_content.extend(self._generate_computed())

        setup_content.extend(self._generate_methods())

        setup_content.extend(self._generate_watch())

        setup_content.extend(self._generate_lifecycle_hooks())

        # Return statement
        return_items = list(self.component.computed.keys()) + list(self.component.methods.keys()) + list(
            self.component.data.keys())
        return_statement = f"{self.indent}{self.indent}return {{"
        return_statement += f"\n{self.indent}{self.indent}{self.indent}" + f",\n{self.indent}{self.indent}{self.indent}".join(
            return_items)
        return_statement += f"\n{self.indent}{self.indent}}};"

        setup_content.append(return_statement)
        setup_content.append(f"{self.indent}}}")

        return "\n".join(setup_content)

    def _generate_store_getters(self):
        content = []
        for name, body in self.component.computed.items():
            if body.startswith('store.getters.'):
                content.append(f"{self.indent}{self.indent}const {name} = computed(() => {body});")
        if content:
            content.append('')
        return content

    def _generate_computed(self):
        content = []
        for name, body in self.component.computed.items():
            if not body.startswith('store.getters.'):
                # Remove 'function()' wrapper
                body = body.replace('function()', '').strip()

                # Check if it's a multi-statement function
                if ';' in body or '\n' in body:
                    if body.startswith('{') and body.endswith('}'):
                        body = body[1:-1].strip()

                    body_lines = body.split(';')
                    indented_body = '\n'.join(
                        f"{self.indent}{self.indent}{self.indent}{line.strip()}"
                        for line in body_lines if line.strip()
                    )
                    content.append(
                        f"{self.indent}{self.indent}const {name} = computed({{\n{indented_body}\n{self.indent}{self.indent}}});"
                    )
                else:
                    if body.startswith('{ ') and body.endswith(' }'):
                        body = body[2:-2].strip()
                    if body.startswith('return '):  # 15 to remove the duplicated ()=>{ as well as return
                        body = body[7:].strip()
                    content.append(f"{self.indent}{self.indent}const {name} = computed(() => {body});")
        if content:
            content.append('')
        return content

    def _generate_reactive_vars(self):
        content = []
        for name, value in self.component.data.items():
            content.append(f"{self.indent}{self.indent}const {name} = ref({value});")
        if content:
            content.append('')
        return content

    def _generate_methods(self):
        content = []
        for name, body in self.component.methods.items():
            formatted_body = self._format_method_body(body)
            content.append(f"{self.indent}{self.indent}const {name} = {formatted_body};")

        if content:
            content.append('')
        return content

    def _format_method_body(self, body):
        # Remove leading/trailing whitespace and 'function' keyword if present
        body = re.sub(r'^\s*function\s*', '', body.strip())

        # Split the function into parameters and body
        match = re.match(r'(\(.*?\))?\s*{(.*)}\s*$', body, re.DOTALL)
        if not match:
            return body  # Return as-is if it doesn't match expected format

        params, body_content = match.groups()
        params = params or '()'

        # Format the body content
        formatted_body = self._format_body_content(body_content)

        # Reconstruct the function as an arrow function
        return f"{params} => {{\n{formatted_body}\n{self.indent}{self.indent}}}"

    def _format_body_content(self, body):
        lines = body.split('\n')
        formatted_lines = []
        indent_level = 1  # Start with one level of indentation inside the function body
        in_object_literal = False

        for line in lines:
            line = line.strip()
            if not line:
                continue  # Skip empty lines

            # Handle opening braces
            if line.endswith('{'):
                formatted_lines.append(f"{self.indent * (indent_level + 2)}{line}")
                indent_level += 1
                if line.startswith('{'):
                    in_object_literal = True
                continue

            # Handle closing braces
            if line.startswith('}'):
                indent_level -= 1
                formatted_lines.append(f"{self.indent * (indent_level + 2)}{line}")
                if line == '}' and in_object_literal:
                    in_object_literal = False
                continue

            # Handle normal lines
            formatted_line = f"{self.indent * (indent_level + 2)}{line}"

            # Add semicolons
            if not line.endswith(';') and not line.endswith('{') and not line.endswith('}') and not in_object_literal:
                formatted_line += ';'

            formatted_lines.append(formatted_line)

        return '\n'.join(formatted_lines)

    def _generate_watch(self):
        content = []
        for name, body in self.component.watch.items():
            # if the name can be found in the props object
            if name in self.component.props:
                content.append(f"{self.indent}{self.indent}watch(() => {name}, {body});")
            else:
                content.append(f"{self.indent}{self.indent}watch({name}, {body});")
        return content

    def _generate_lifecycle_hooks(self):
        content = []
        lifecycle_mapping = {
            'created': 'onBeforeMount',
            'mounted': 'onMounted',
            'beforeDestroy': 'onBeforeUnmount'
        }
        for hook, body in self.component.lifecycle_hooks.items():
            vue3_hook = lifecycle_mapping.get(hook, hook)
            content.append(
                f"{self.indent}{self.indent}{vue3_hook}({self.indent}{self.indent}{self.indent}{body}\n{self.indent}{self.indent});")
        return content

    def fix_this(self, setup):
        for prop in self.component.props:
            setup = re.sub(r'\bthis\.' + prop + r'\b', 'props.' + prop, setup)

        for data in self.component.data:
            setup = re.sub(r'\bthis\.' + data + r'\b', data + '.value', setup)

        for method in self.component.methods:
            setup = re.sub(r'\bthis\.' + method + r'\b', method, setup)

        for computed in self.component.computed:
            setup = re.sub(r'\bthis\.' + computed + r'\b', computed + '.value', setup)

        return setup

    def add_root_instance(self, script, imports):
        if re.search(r'this\.\$\w+', script):
            setup_match = re.search(r'(setup\s*\([^)]*\)\s*{)', script)
            if setup_match:
                setup_start = setup_match.start(1)
                setup_end = setup_match.end(1)

                # Prepare the lines to insert
                insert_lines = f"\n{self.indent * 2}const instance = getCurrentInstance();\n{self.indent * 2}const root = instance.proxy.$root;\n"

                modified_script = (
                        script[:setup_end] +
                        insert_lines +
                        script[setup_end:]
                )

                vue_import_match = re.search(r'import\s*{([^}]*)}\s*from\s*[\'"]vue[\'"]', imports)
                if vue_import_match:
                    current_imports = vue_import_match.group(1)
                    if 'getCurrentInstance' not in current_imports:
                        new_imports = current_imports + ', getCurrentInstance'
                        new_imports = ', '.join(sorted(set(new_imports.replace(' ', '').split(','))))
                        updated_import = f"import {{ {new_imports} }} from 'vue'"
                        imports = imports.replace(vue_import_match.group(0), updated_import)
                else:
                    imports += "\nimport { getCurrentInstance } from 'vue';"

                return modified_script, imports

        # If no modifications were made, return the original content
        return script, imports

    def fix_nextTick(self, script, imports):
        if re.search(r'this\.\$nextTick', script):
            # Replace this.$nextTick with nextTick
            script = re.sub(r'this\.\$nextTick', 'nextTick', script)

            vue_import_match = re.search(r'import\s*{([^}]*)}\s*from\s*[\'"]vue[\'"]', imports)
            if vue_import_match:
                current_imports = vue_import_match.group(1)
                if 'nextTick' not in current_imports:
                    new_imports = current_imports + ', nextTick'
                    new_imports = ', '.join(sorted(set(new_imports.replace(' ', '').split(','))))
                    updated_import = f"import {{ {new_imports} }} from 'vue';"
                    imports = imports.replace(vue_import_match.group(0), updated_import)
            else:
                imports += "\nimport { nextTick } from 'vue';"

            return script, imports

        return script, imports
