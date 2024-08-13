import re
import esprima
from Vue2Component import Vue2Component

class Vue2Scanner:
    def __init__(self, content):
        self.content = content
        self.component = Vue2Component()

    def scan(self):
        script_content = self._extract_script_content()
        if not script_content:
            print("DEBUG: No script content found")
            return self.component

        try:
            parsed = esprima.parseModule(script_content)
            self._scan_imports(parsed)
            self._scan_export_default(parsed)
        except Exception as e:
            print(f"Error parsing script content: {str(e)}")

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

    def _scan_export_default(self, parsed):
        for node in parsed.body:
            if node.type == 'ExportDefaultDeclaration':
                if node.declaration.type == 'ObjectExpression':
                    self._scan_component_object(node.declaration)

    def _scan_component_object(self, obj):
        for prop in obj.properties:
            if prop.key.name == 'name':
                self._scan_name(prop.value)
            elif prop.key.name == 'data':
                self._scan_data(prop.value)
            elif prop.key.name == 'components':
                self._scan_components(prop.value)
            elif prop.key.name == 'mixins':
                self._scan_mixins(prop.value)
            elif prop.key.name == 'props':
                self._scan_props(prop.value)
            elif prop.key.name == 'computed':
                self._scan_computed(prop.value)
            elif prop.key.name == 'methods':
                self._scan_methods(prop.value)
            elif prop.key.name == 'watch':
                self._scan_watch(prop.value)
            elif prop.key.name in ['created', 'mounted', 'beforeDestroy']:
                self._scan_lifecycle_hook(prop.key.name, prop.value)

    def _scan_mixins(self, node):
        if node.type == 'ArrayExpression':
            for element in node.elements:
                if element.type == 'Identifier':
                    self.component.mixins.append(element.name)
        print(f"DEBUG: Scanned mixins: {self.component.mixins}")

    def _scan_data(self, node):
        if node.type == 'FunctionExpression':
            # Extract the return statement from the function body
            return_statement = next((stmt for stmt in node.body.body if stmt.type == 'ReturnStatement'), None)

            if return_statement and return_statement.argument.type == 'ObjectExpression':
                # Process each property in the returned object
                for prop in return_statement.argument.properties:
                    if prop.type == 'Property':
                        key = prop.key.name
                        value = self._node_to_string(prop.value)
                        self.component.data[key] = value

        print(f"DEBUG: Scanned data: {self.component.data}")

    def _scan_watch(self, node):
        if node.type == 'ObjectExpression':
            for prop in node.properties:
                name = prop.key.name
                body = self._node_to_string(prop.value)
                self.component.watch[name] = body
        print(f"DEBUG: Scanned watch: {self.component.watch}")

    def _scan_lifecycle_hook(self, hook_name, node):
        body = self._node_to_string(node)
        self.component.lifecycle_hooks[hook_name] = body
        print(f"DEBUG: Scanned lifecycle hook {hook_name}: {body}")

    def _scan_name(self, node):
        if node.type == 'Literal':
            self.component.name = node.value
        print(f"DEBUG: Scanned name: {self.component.name}")

    def _scan_components(self, node):
        if node.type == 'ObjectExpression':
            for prop in node.properties:
                if prop.type == 'Property' and prop.value.type == 'Identifier':
                    self.component.components[prop.key.name] = prop.value.name
                else:
                    self.component.components[prop.key.name] = self._node_to_string(prop.value)
        print(f"DEBUG: Scanned components: {self.component.components}")

    def _get_prop_value(self, node):
        if isinstance(node, str):
            return node
        if not hasattr(node, 'type'):
            return str(node)

        if node.type == 'Identifier':
            print(f"DEBUG: Found identifier: {node.name}")
            return node.name
        elif node.type == 'ObjectExpression':
            return {p.key.name: self._get_prop_value(p.value) for p in node.properties}
        elif node.type == 'Literal':
            return node.value
        elif node.type == 'ArrowFunctionExpression':
            params = ', '.join([self._node_to_string(p) for p in node.params])
            body = self._node_to_string(node.body)
            if getattr(node, 'expression', False):
                return f"() => {body}"
            else:
                return f"() => {{}}"
        elif node.type == 'FunctionExpression':
            params = ', '.join([self._node_to_string(p) for p in node.params])
            body = self._node_to_string(node.body)
            return f"function({params}) {body}"
        else:
            return self._node_to_string(node)

    def _scan_props(self, node):
        if node.type == 'ObjectExpression':
            for prop in node.properties:
                prop_name = prop.key.name
                prop_value = self._get_prop_value(prop.value)
                if isinstance(prop_value, dict) and 'default' in prop_value:
                    prop_value['default'] = self._get_prop_value(prop_value['default'])
                self.component.props[prop_name] = prop_value
        print(f"DEBUG: Scanned props: {self.component.props}")

    def _scan_methods(self, node):
        if node.type == 'ObjectExpression':
            for prop in node.properties:
                name = prop.key.name
                body = self._node_to_string(prop.value)
                self.component.methods[name] = body
        self.component.has_setup_content = bool(self.component.methods)
        print(f"DEBUG: Scanned methods: {self.component.methods}")

    def _scan_computed(self, properties):
        for prop in properties.properties:
            if prop.type == 'SpreadElement':
                self._scan_mapgetters(prop.argument)
            elif prop.type == 'Property':
                name = prop.key.name
                body = self._node_to_string(prop.value)
                # remove () => { return ... } from computed properties using regex
                body = re.sub(r'\(\) => \{ return (.*)\}', r'\1', body)
                self.component.computed[name] = body
            else:
                print(f"DEBUG: Unexpected property type in computed: {prop.type}")

        print(f"DEBUG: Final computed properties: {self.component.computed}")

    def _scan_mapgetters(self, node):
        if node.type == 'CallExpression' and node.callee.name == 'mapGetters':
            self.component.uses_vuex = True
            if node.arguments and hasattr(node.arguments[0], 'type') and node.arguments[0].type == 'ArrayExpression':
                for element in node.arguments[0].elements:
                    if hasattr(element, 'type') and element.type == 'Literal':
                        getter_name = element.value
                        self.component.computed[getter_name] = f"store.getters.{getter_name}"
                    else:
                        print(f"DEBUG: Unexpected element type in mapGetters: {getattr(element, 'type', 'Unknown')}")
            else:
                print("DEBUG: Unexpected argument structure in mapGetters call")

    def _node_to_string(self, node):
        if node is None:
            return "None"

        if node.type in ['FunctionExpression', 'ArrowFunctionExpression']:
            async_prefix = "async " if getattr(node, 'async', False) else ""
            params = ', '.join([self._param_to_string(p) for p in node.params])
            body = self._node_to_string(node.body)
            if node.type == 'ArrowFunctionExpression':
                if len(node.params) == 1:
                    return f"{async_prefix}({params}) => {body}"
                return f"{async_prefix}({params}) => {body}"
            else:  # FunctionExpression
                return f"{async_prefix}function({params}) {body}"

        elif node.type == 'BlockStatement':
            statements = [self._node_to_string(stmt) for stmt in node.body]
            return '{ ' + '; '.join(statements) + ' }'

        elif node.type == 'ReturnStatement':
            return f"return {self._node_to_string(node.argument)}"

        elif node.type == 'IfStatement':
            condition = self._node_to_string(node.test)
            consequent = self._node_to_string(node.consequent)
            alternate = self._node_to_string(node.alternate) if node.alternate else None
            if alternate:
                return f"if ({condition}) {consequent} else {alternate}"
            else:
                return f"if ({condition}) {consequent}"

        elif node.type == 'TryStatement':
            try_block = self._node_to_string(node.block)
            catch_clause = ""
            if node.handler:
                catch_param = self._node_to_string(node.handler.param) if node.handler.param else ""
                catch_body = self._node_to_string(node.handler.body)
                catch_clause = f" catch ({catch_param}) {catch_body}"
            finally_block = f" finally {self._node_to_string(node.finalizer)}" if node.finalizer else ""
            return f"try {try_block}{catch_clause}{finally_block}"

        elif node.type == 'AwaitExpression':
            argument = self._node_to_string(node.argument)
            return f"await {argument}"

        elif node.type == 'CatchClause':
            param = self._node_to_string(node.param) if node.param else ""
            body = self._node_to_string(node.body)
            return f"catch ({param}) {body}"

        elif node.type == 'ExpressionStatement':
            return self._node_to_string(node.expression)

        elif node.type == 'AssignmentExpression':
            left = self._node_to_string(node.left)
            right = self._node_to_string(node.right)
            return f"{left} = {right};"

        elif node.type == 'VariableDeclaration':
            declarations = [self._node_to_string(decl) for decl in node.declarations]
            return f"{node.kind} {', '.join(declarations)}"

        elif node.type == 'VariableDeclarator':
            id_str = self._node_to_string(node.id)
            init_str = self._node_to_string(node.init) if node.init else None
            return f"{id_str} = {init_str}" if init_str else id_str

        elif node.type == 'BinaryExpression':
            left = self._node_to_string(node.left)
            right = self._node_to_string(node.right)
            return f"{left} {node.operator} {right}"

        elif node.type == 'UnaryExpression':
            argument = self._node_to_string(node.argument)
            if node.operator == '!' and node.argument.type == 'LogicalExpression':
                return f"{node.operator}({argument})"
            return f"{node.operator}{argument}"

        elif node.type == 'LogicalExpression':
            left = self._node_to_string(node.left)
            right = self._node_to_string(node.right)
            if node.left.type == 'LogicalExpression' and node.left.operator != node.operator:
                left = f"({left})"
            if node.right.type == 'LogicalExpression' and node.right.operator != node.operator:
                right = f"({right})"
            return f"{left} {node.operator} {right}"

        elif node.type == 'Literal':
            if isinstance(node.value, bool):
                return str(node.value).lower()
            return repr(node.value)

        elif node.type == 'Identifier':
            return node.name

        elif node.type == 'MemberExpression':
            obj = self._node_to_string(node.object)
            if node.computed:
                prop = self._node_to_string(node.property)
                return f"{obj}[{prop}]"
            else:
                prop = node.property.name if hasattr(node.property, 'name') else self._node_to_string(node.property)
                return f"{obj}.{prop}"

        elif node.type == 'CallExpression':
            callee = self._node_to_string(node.callee)
            args = ', '.join([self._node_to_string(arg) for arg in node.arguments])
            return f"{callee}({args})"

        elif node.type == 'ThisExpression':
            return 'this'

        elif node.type == 'ArrayExpression':
            elements = [self._node_to_string(el) for el in node.elements]
            return f"[{', '.join(elements)}]"

        elif node.type == 'ObjectExpression':
            properties = []
            for p in node.properties:
                if p.type == 'SpreadElement':
                    properties.append(f"...{self._node_to_string(p.argument)}")
                elif p.type == 'Property':
                    key = p.key.name if hasattr(p.key, 'name') else self._node_to_string(p.key)
                    value = self._node_to_string(p.value)
                    properties.append(f"{key}: {value}")
            return f"{{{', '.join(properties)}}}"

        elif node.type == 'ConditionalExpression':
            test = self._node_to_string(node.test)
            consequent = self._node_to_string(node.consequent)
            alternate = self._node_to_string(node.alternate)
            return f"({test} ? {consequent} : {alternate})"

        elif node.type == 'ObjectPattern':
            properties = [self._node_to_string(p) for p in node.properties]
            return f"{{ {', '.join(properties)} }}"

        elif node.type == 'Property':
            if node.shorthand:
                return node.key.name
            key = node.key.name if hasattr(node.key, 'name') else self._node_to_string(node.key)
            value = self._node_to_string(node.value)

            return f"{key}: {value}"
        elif node.type == 'TemplateLiteral':
            quasis = [self._node_to_string(q) for q in node.quasis]
            expressions = [self._node_to_string(e) for e in node.expressions]
            parts = []
            for i in range(len(quasis)):
                parts.append(quasis[i])
                if i < len(expressions):
                    parts.append(f"${{{expressions[i]}}}")
            return f"`{''.join(parts)}`"

        elif node.type == 'TemplateElement':
            return node.value.cooked

        elif node.type == 'SpreadElement':
            return f"...{self._node_to_string(node.argument)}"

        elif node.type == 'SwitchStatement':
            discriminant = self._node_to_string(node.discriminant)
            cases = [self._node_to_string(case) for case in node.cases]
            return f"switch ({discriminant}) {{{' '.join(cases)}}}"

        elif node.type == 'SwitchCase':
            if node.test:
                test = self._node_to_string(node.test)
                consequent = '; '.join([self._node_to_string(stmt) for stmt in node.consequent])
                return f"case {test}: {consequent}"
            else:
                consequent = '; '.join([self._node_to_string(stmt) for stmt in node.consequent])
                return f"default: {consequent}"

        elif node.type == 'BreakStatement':
            if node.label:
                return f"break {self._node_to_string(node.label)};"
            else:
                return "break;"

        elif node.type == 'NewExpression':
            callee = self._node_to_string(node.callee)
            args = ', '.join([self._node_to_string(arg) for arg in node.arguments])
            return f"new {callee}({args})"

        else:
            return f"/* Unsupported node type: {node.type} */"


    def _param_to_string(self, param):
        if param.type == 'Identifier':
            return param.name
        elif param.type == 'ObjectPattern':
            properties = [self._node_to_string(p) for p in param.properties]
            return f"{{ {', '.join(properties)} }}"
        else:
            return f"/* Unsupported parameter type: {param.type} */"

    def _scan_imports(self, parsed):
        for node in parsed.body:
            if node.type == 'ImportDeclaration':
                source = node.source.value
                default_specifiers = []
                named_specifiers = []
                for specifier in node.specifiers:
                    if specifier.type == 'ImportDefaultSpecifier':
                        default_specifiers.append(specifier.local.name)
                    elif specifier.type == 'ImportSpecifier':
                        named_specifiers.append(specifier.imported.name)

                if default_specifiers and named_specifiers:
                    import_str = f"import {', '.join(default_specifiers)}, {{ {', '.join(named_specifiers)} }} from '{source}'"
                elif default_specifiers:
                    import_str = f"import {', '.join(default_specifiers)} from '{source}'"
                elif named_specifiers:
                    import_str = f"import {{ {', '.join(named_specifiers)} }} from '{source}'"
                else:
                    continue

                self.component.imports.add(import_str)
        print(f"DEBUG: Scanned imports: {self.component.imports}")