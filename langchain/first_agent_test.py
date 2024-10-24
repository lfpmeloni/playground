import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains.llm_math.base import LLMMathChain
from langchain_community.tools import DuckDuckGoSearchResults
from langchain.agents import create_react_agent, Tool

# Load environment variables from .env file
load_dotenv()

# Fetch the OpenAI API key from the environment variable
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OpenAI API key not found in .env file")

# Initialize the OpenAI model (using gpt-4o-mini)
llm = ChatOpenAI(openai_api_key=openai_api_key, model="gpt-4o-mini", temperature=0)

# Use the from_llm method to instantiate LLMMathChain
math_chain = LLMMathChain.from_llm(llm=llm)

# Define the tools the agent can use (DuckDuckGo search and LLMMathChain for math)
tools = [
    Tool(
        name="Search",
        func=DuckDuckGoSearchResults().run,
        description="Useful for searching the web for current information."
    ),
    Tool(
        name="Calculator",
        func=math_chain.invoke,
        description="Useful for performing math calculations."
    )
]

# Prepare a string of tool names
tool_names = ", ".join(tool.name for tool in tools)

# Define the prompt template that the agent will follow
template = '''
Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought: {agent_scratchpad}
'''

# Create the prompt template with the necessary input variables
prompt = PromptTemplate.from_template(template)

# Create the agent with the prompt
agent = create_react_agent(
    tools=tools,
    llm=llm,
    prompt=prompt
)

# Prepare the input as a dictionary, including intermediate_steps
input_data = {
    "input": "What is 25 * 4? Can you also search for the latest news about AI?",
    "tools": tools,
    "tool_names": tool_names,
    "agent_scratchpad": "",  # Initial scratchpad can be empty
    "intermediate_steps": []  # Initialize intermediate steps as an empty list
}

# Use invoke to ask the agent to perform the task
action_result = agent.invoke(input_data)

# Process the results for both actions
if action_result.tool == "Calculator":
    # Perform the calculation
    final_calculation = math_chain.invoke(action_result.tool_input)
    print("Calculation Result:", final_calculation)
    
    # Now search for the latest news about AI
    action_result.tool = "Search"
    action_result.tool_input = "latest news about AI"
    
    # Perform the search
    search_result = DuckDuckGoSearchResults().run(action_result.tool_input)
    print("Search Results:", search_result)
else:
    print("No valid tool action detected.")
