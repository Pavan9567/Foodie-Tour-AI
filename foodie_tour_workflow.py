import os
import yaml
import asyncio
from julep import AsyncClient
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("JULEP_API_KEY")
base_url = "https://api.julep.ai/api"
client = AsyncClient(api_key=api_key, base_url=base_url)


workflow_yaml = """
name: FoodieTourGenerator
description: Generate a one-day foodie tour for a list of cities, considering weather, iconic dishes, and top restaurants.
input_schema:
    type: object
    required: ["cities"]
    properties:
        cities:
            type: array
            items:
                type: string
            description: List of cities for the foodie tour
tools:
    - name: weather
      type: integration
      integration:
        provider: weather
        method: get
        setup:
            openweathermap_api_key: {OPENWEATHERMAP_API_KEY}
    - name: internet_search
      type: integration
      integration:
        provider: brave
        method: search
        setup:
            api_key: {BRAVE_API_KEY}
main:
    - over: $ steps[0].input.cities
      map:
        - tool: weather
          arguments:
            location: $ _
        - prompt:
            - role: system
              content: You are a culinary expert. Based on the weather in {steps[0].output.location}, suggest whether indoor or outdoor dining is preferable. If temperature is below 15°c or there is precipitation, recommend indoor dining: otherwise, recommend outdoor dining.
        - tool: internet_search
          arguments:
            query: $ 'iconic dishes in ' + _
        - prompt:
            - role: system
              content: From the search results, select three iconic dishes for {steps[0].output.location}. Provide a brief description of each dish.
        - tool: internet_search
          arguments:
            query: $ 'top-rated restaurants in ' + _ + ' serving ' + steps[3].output[0].name
        - tool: internet_search
          arguments:
            query: $ 'top-rated restaurants in ' + _ + ' serving ' + steps[3].output[1].name
        - tool: internet_search
          arguments:
            query: $ 'top-rated restaurants in ' + _ + ' serving ' + steps[3].output[2].name
        - prompt:
            - role: system
              content: |
                Create a one-day foodie tour narrative for {steps[0].output.location}, considering the weather ({steps[1].output}) and the following:
                - Iconic dishes: {steps[3].output}
                - Top restaurants: {steps[4].output}, {steps[5].output}, {steps[6].output}
                Plan breakfast, lunch, and dinner, each at a different restaurant, serving one of the iconic dishes. Include weather considerations in the narrative (e.g., cozy indoor setting if rainy, vibrant outdoor patio if sunny). Return a structured response with:
                - City
                - Weather
                - Dining Preference (indoor/outdoor)
                - Breakfast (restaurant, dish, narrative)
                - Lunch (restaurant, dish, narrative)
                - Dinner (restaurant, dish, narrative)
    - prompt:
        - role: system
          content: Combine the foodie tour narratives for all cities into a single report.
"""

async def create_and_run_workflow():
    try:
        workflow_definition = workflow_yaml.format(
            OPENWEATHERMAP_API_KEY=os.getenv("OPENWEATHERMAP_API_KEY"),
            BRAVE_API_KEY=os.getenv("BRAVE_API_KEY")
        )

        task_definition = yaml.safe_load(workflow_definition)

        agent = await client.agents.create(
            name="FoodieTourAgent",
            model="claude-3.5-sonnet",
            about="An AI assistant specializing in culinary tours and recommendations."
        )

        task = await client.tasks.create(
            agent_id=agent.id,
            **task_definition
        )

        execution = await client.executions.create(
            task_id=task.id,
            input={"cities": cities}
        )

        while True:
            status = await client.executions.get(execution.id)
            if status.status in ["succeded", "failed"]:
                break
            await asyncio.sleep(5)

        if status.status == "succeeded":
            print("Workflow Output:", status.output)
        else:
            print("Workflow failed:", status.error)
    
    except Exception as e:
        print(f"Error: {e}")

def get_cities_from_user():
    print("Enter the cities for the foodie tour (one per line). Press Enter twice to finish:")
    cities = []
    while True:
        city = input().strip()
        if city == "":
            if cities:
                break
            else:
                print("Please enter at least one city.")
                continue
        cities.append(city)
    return cities


if __name__ == "__main__":
    cities = get_cities_from_user()
    asyncio.run(create_and_run_workflow(cities))