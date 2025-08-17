from langchain.tools import Tool



def print_hello(data: str)-> str:
    return "Hello from the custom tool!"

print_hello_tool = Tool(
    name="hello_tool",
    func=print_hello,
    description="A simple tool that returns a hello message.",
)