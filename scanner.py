import re
from Vue2Component import Vue2Component


def _parse_props(props_content):
    props = {}
    brace_count = 0
    current_prop = None
    current_value = []
    in_string = False
    string_delimiter = None

    for char in props_content:
        if char in ['"', "'"]:
            if not in_string:
                in_string = True
                string_delimiter = char
            elif string_delimiter == char:
                in_string = False
                string_delimiter = None

        if not in_string:
            if char == '{':
                brace_count += 1
                if brace_count == 1 and current_prop is None:
                    continue
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    if current_prop:
                        props[current_prop] = ''.join(current_value).strip()
                        print(f"DEBUG: Added prop: {current_prop} = {props[current_prop]}")
                    current_prop = None
                    current_value = []
                    continue
            elif char == ',' and brace_count == 1:
                if current_prop:
                    props[current_prop] = ''.join(current_value).strip()
                    print(f"DEBUG: Added prop: {current_prop} = {props[current_prop]}")
                current_prop = None
                current_value = []
                continue
            elif char == ':' and brace_count == 1:
                current_prop = ''.join(current_value).strip()
                current_value = []
                continue

        if brace_count > 0 or char.strip():
            current_value.append(char)

    print(f"DEBUG: Parsed props: {props}")
    return props


class Vue2Scanner:
    def __init__(self, content):
        self.content = content
        self.component = Vue2Component()

    def scan(self):
        script_content = self._extract_script_content()
        if not script_content:
            print("DEBUG: No script content found")
            return self.component

        self._scan_name(script_content)
        self._scan_components(script_content)
        self._scan_props(script_content)
        self._scan_computed(script_content)
        self._scan_methods(script_content)
        self._scan_imports(script_content)

        return self.component

    def _extract_script_content(self):
        script_match = re.search(r'<script>([\s\S]*?)<\/script>', self.content)
        if script_match:
            script_content = script_match.group(1)
            print(f"DEBUG: Extracted script content:\n{script_content}")
            return script_content
        else:
            print("DEBUG: No script content found")
            return ""

    def _scan_name(self, script_content):
        print(f"DEBUG: Searching for name")
        name_match = re.search(r'name:\s*[\'"](\w+(?:-\w+)*)[\'"]', script_content, re.MULTILINE | re.DOTALL)
        if name_match:
            self.component.name = name_match.group(1)
            print(f"DEBUG: Found name: {self.component.name}")
        else:
            print("DEBUG: Name not found")
        print(f"DEBUG: Scanned name: {self.component.name}")

    def _scan_props(self, script_content):
        print(f"DEBUG: Searching for props")
        props_start_match = re.search(r'props:\s*\{', script_content)

        if props_start_match:
            start_index = props_start_match.end() - 1  # Start after 'props: {'
            brace_count = 1
            end_index = start_index

            # Iterate through the script content to find the matching closing brace
            while brace_count > 0 and end_index < len(script_content):
                end_index += 1
                char = script_content[end_index]
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1

            props_content = script_content[start_index:end_index + 1]
            print(f"DEBUG: Found props content:\n{props_content}")
            self.component.props = _parse_props(props_content)
        else:
            print("DEBUG: Props not found")

        print(f"DEBUG: Scanned props: {self.component.props}")

    def _scan_components(self, script_content):
        components_match = re.search(r'components:\s*({[\s\S]*?})', script_content)
        if components_match:
            components_content = components_match.group(1)
            components = re.findall(r'(\w+)(?:\s*:\s*\w+)?', components_content)
            self.component.components = {comp: comp for comp in components}
        print(f"DEBUG: Scanned components: {self.component.components}")

    def _scan_computed(self, script_content):
        computed_match = re.search(r'computed:\s*({[\s\S]*?})', script_content)
        if computed_match:
            self.component.has_setup_content = True
            computed_content = computed_match.group(1)
            self._scan_mapgetters(computed_content)
            self._scan_other_computed(computed_content)
        print(f"DEBUG: Scanned computed: {self.component.computed}")

    def _scan_mapgetters(self, computed_content):
        mapgetters_match = re.search(r'\.{3}mapGetters\(\[([\s\S]*?)\]\)', computed_content)
        if mapgetters_match:
            self.component.has_setup_content = True
            self.component.uses_vuex = True
            getters = re.findall(r'[\'"](\w+)[\'"]', mapgetters_match.group(1))
            for getter in getters:
                self.component.computed[getter] = f"store.getters.{getter}"
        print(f"DEBUG: Scanned mapGetters: {self.component.computed}")

    def _scan_other_computed(self, computed_content):
        other_computed = re.findall(r'(\w+)\s*\([^)]*\)\s*{([\s\S]*?)}', computed_content)
        for name, body in other_computed:
            self.component.computed[name] = body.strip()
        print(f"DEBUG: Scanned other computed: {self.component.computed}")

    def _scan_methods(self, script_content):
        methods_match = re.search(r'methods:\s*({[\s\S]*?})', script_content)
        if methods_match:
            self.component.has_setup_content = True
            methods_content = methods_match.group(1)
            methods = re.findall(r'(\w+)\s*\((.*?)\)\s*{([\s\S]*?)}', methods_content, re.DOTALL)
            self.component.methods = {name: (params.strip(), body.strip()) for name, params, body in methods}
        print(f"DEBUG: Scanned methods: {self.component.methods}")

    def _scan_imports(self, script_content):
        import_matches = re.findall(r'import.*?(?:from\s+[\'"].*?[\'"]|[\'"].*?[\'"]).*?;?', script_content, re.DOTALL)
        for import_match in import_matches:
            self.component.imports.add(import_match.strip().rstrip(';'))
        print(f"DEBUG: Scanned imports: {self.component.imports}")