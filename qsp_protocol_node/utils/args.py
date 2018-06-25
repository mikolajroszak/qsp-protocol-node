def replace_args(template, args):
    """
    Injects a set of input arguments into the command template, returning a
    command instance.
    """
    cmd = template
    for name in args:
        cmd = cmd.replace(name, args[name])
    return cmd
