from langgraph.prebuilt import create_react_agent

def init_agent(model, tools):
    agent = create_react_agent(model, tools)
    agent.llm = model
    return agent
