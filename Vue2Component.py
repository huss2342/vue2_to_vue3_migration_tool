class Vue2Component:
    def __init__(self):
        self.name = ""
        self.components = {}
        self.props = {}
        self.data = {}
        self.computed = {}
        self.mixins = []
        self.methods = {}
        self.watch = {}
        self.lifecycle_hooks = {}
        self.imports = set()
        self.uses_vuex = False
        self.has_setup_content = False
