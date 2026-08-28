import needle

def build_agent(tools, system):
    return needle.Needle(
        tools=tools,
        system=system,
    )
