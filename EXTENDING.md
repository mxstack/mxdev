# Extending mxdev with Hooks

The functionality of mxdev can be extended by hooks.
This is useful to generate additional scripts or files or automate any other setup steps related to mxdev's domain.

## Configuration

Extension configuration settings end up in the `mx.ini` file.
They can be added globally to the `settings` section, as dedicated config sections or package specific.
To avoid naming conflicts, all hook-related settings and config sections must be prefixed with a namespace.

It is recommended to use the package name containing the hook as a namespace.

This looks like so:

```INI
[settings]
myextension-global_setting = 1

[myextension-section]
setting = value

[foo.bar]
myextension-package_setting = 1
```

## Implementation

The extension is implemented as a subclass of `mxdev.Hook`:

```Python
from mxdev import Hook
from mxdev import State

class MyExtension(Hook):

    namespace = "myextension"
    """The namespace for this hook."""

    def read(self, state: State) -> None:
        """Gets executed after mxdev read operation."""
        # Access configuration from state
        # - state.configuration.settings: main [settings] section
        # - state.configuration.packages: package sections
        # - state.configuration.hooks: hook-related sections

        # Example: Access your hook's settings
        global_setting = state.configuration.settings.get('myextension-global_setting')

        # Example: Access hook-specific sections
        for section_name, section_config in state.configuration.hooks.items():
            if section_name.startswith('myextension-'):
                # Process your hook's configuration
                pass

    def write(self, state: State) -> None:
        """Gets executed after mxdev write operation."""
        # Generate additional files, scripts, etc.
        # Access generated requirements/constraints from:
        # - state.requirements
        # - state.constraints
```

## State Object

The `State` object passed to hooks contains:

- **`state.configuration`**: Configuration object with:
  - `settings`: Dict of main [settings] section
  - `packages`: Dict of package sections
  - `hooks`: Dict of hook-related sections

- **`state.requirements`**: List of requirement lines (after write phase)

- **`state.constraints`**: List of constraint lines (after write phase)

## Registration

The hook must be registered as an entry point in the `pyproject.toml` of your package:

```TOML
[project.entry-points.mxdev]
myextension = "mypackage:MyExtension"
```

Replace:
- `myextension`: The name users will reference
- `mypackage`: Your Python package name
- `MyExtension`: Your Hook subclass

## Hook Lifecycle

1. **Read phase**: mxdev reads configuration and fetches sources
   - All hooks' `read()` methods are called

2. **Write phase**: mxdev writes requirements and constraints
   - All hooks' `write()` methods are called

## Namespace Convention

- Use your package name as namespace prefix
- All settings: `namespace-setting_name`
- All sections: `[namespace-section]`
- This prevents conflicts with other hooks

## Example Use Cases

- Generate additional configuration files (e.g., buildout.cfg, docker-compose.yml)
- Create wrapper scripts for development
- Generate IDE project files
- Export dependency graphs
- Integrate with other tools (pytest, tox, pre-commit)

## Best Practices

1. **Fail gracefully**: If your hook can't complete, log warnings instead of raising exceptions
2. **Document your settings**: Provide clear documentation for all configuration options
3. **Use namespaces**: Always prefix settings with your namespace
4. **Be minimal**: Don't add heavy dependencies to your hook package
5. **Test thoroughly**: Hooks run after mxdev's core operations, ensure they don't break workflows

## See Also

- [mxdev main documentation](README.md)
- [Hook base class source](src/mxdev/hooks.py)
- [State object source](src/mxdev/state.py)
