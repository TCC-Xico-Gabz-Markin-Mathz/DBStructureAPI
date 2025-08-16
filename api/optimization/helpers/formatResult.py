def format_sql_commands(sql_arrays):
    """
    Converte um array de arrays de comandos SQL em uma lista única

    Args:
        sql_arrays (list): Array de arrays contendo comandos SQL

    Returns:
        list: Lista única de comandos SQL prontos para execução
    """
    if not isinstance(sql_arrays, list):
        return ["-- Erro: A entrada deve ser um array"]

    flattened_commands = []
    for array in sql_arrays:
        if isinstance(array, list):
            for cmd in array:
                if isinstance(cmd, str) and cmd.strip():
                    flattened_commands.append(cmd.strip())
        elif isinstance(array, str) and array.strip():
            flattened_commands.append(array.strip())

    return flattened_commands
