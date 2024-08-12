import re
import jsbeautifier


class Vue3Generator:
    def __init__(self, component):
        self.component = component
        self.indent = "    "

    def generate(self):
        imports = self._generate_imports()
        components = self._generate_components()
        props = self._generate_props()
        setup = self._generate_setup()

        # fixing syntax then making it look prettier
        setup = re.sub(r';;\s*$', ';', setup, flags=re.MULTILINE)
        setup = re.sub(r'\)\s*$', ');', setup, flags=re.MULTILINE)
        setup = re.sub(r"this\.\$store", r'store', setup)
        setup = self.fix_this(setup)

        props_count = len(re.findall(r'\bprops\b', setup))
        if props_count == 1:
            setup = re.sub(r'\bprops\b', '', setup)

        options = jsbeautifier.default_options()
        options.wrap_line_length = 149
        setup = jsbeautifier.beautify(setup, options)

        # starting
        component_content = f"{self.indent}name: '{self.component.name}'"
        if components:
            component_content += f",\n{components}"

        if props:
            component_content += f",\n{self.indent}props: {{\n{props}\n{self.indent}}}"

        if setup:
            component_content += f",\n{setup}"

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

        imports.append(f"import {{ {', '.join(sorted(vue_imports))} }} from 'vue';")

        if self.component.uses_vuex:
            imports.append("import { useStore } from 'js/store';")

        for import_statement in self.component.imports:
            if 'vuex' not in import_statement and 'mapGetters' not in import_statement:
                imports.append(import_statement + ";")
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

            # Remove single quotes around words using regex
            prop_string = re.sub(r"'(\w+)'", r'\1', prop_string)
            prop_string = re.sub(r"True", r'true', prop_string)
            prop_string = re.sub(r"{(.*)}", r'{ \1 }', prop_string)
            prop_string = re.sub(r"False", r'false', prop_string)
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

        # Add reactive variables
        setup_content.extend(self._generate_reactive_vars())

        # Add store.getters
        setup_content.extend(self._generate_store_getters())

        # Add computed properties
        setup_content.extend(self._genertate_computed())

        # Add methods
        setup_content.extend(self._generate_methods())

        # Add watch
        setup_content.extend(self._generate_watch())

        # Add lifecycle hooks
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

    def _genertate_computed(self):
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
            # Remove 'function' keyword if present
            body = re.sub(r'^function\s*', '', body.strip())

            # Convert to arrow function if it's not already
            if not '=>' in body:
                body = body.replace('{', '=> {', 1)

            content.append(f"{self.indent}{self.indent}const {name} = {body};")
        if content:
            content.append('')
        return content

    def _generate_watch(self):
        content = []
        for name, body in self.component.watch.items():
            # if the name starts with 'props.'
            if name.startswith('props.'):
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
