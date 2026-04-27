import sys
import os

print(f"Python Version: {sys.version}")
print(f"CWD: {os.getcwd()}")

try:
    import langchain
    print(f"LangChain Version: {langchain.__version__}")
    print(f"LangChain Path: {langchain.__file__}")
except ImportError:
    print("LangChain NOT installed.")

try:
    from langchain.agents import AgentExecutor
    print("SUCCESS: Imported AgentExecutor from langchain.agents")
except ImportError as e:
    print(f"FAIL: langchain.agents.AgentExecutor: {e}")

try:
    from langchain.agents.agent_executor import AgentExecutor
    print("SUCCESS: Imported AgentExecutor from langchain.agents.agent_executor")
except ImportError as e:
    print(f"FAIL: langchain.agents.agent_executor.AgentExecutor: {e}")

try:
    import langchain.agents
    print(f"langchain.agents members: {dir(langchain.agents)}")
except Exception as e:
    print(f"Error inspecting langchain.agents: {e}")
