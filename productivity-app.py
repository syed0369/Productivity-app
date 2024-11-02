import datetime
from neo4j import GraphDatabase

class QuestionParser:

    def __init__(self, app, user_id):
        self.app = app
        self.user_id = user_id

    def parse_question(self, prompt):
        prompt = prompt.lower() 
        
        if "item" in prompt or "shop" in prompt or "amount" in prompt:          
            return self._parse_shopping_items()

        elif "spot" in prompt or "city" in prompt or "travelling" in prompt or "destination" in prompt or "vacation" in prompt or "cities" in prompt or "place" in prompt:
            return self._parse_vacation_places()
        
        elif "work" in prompt or "task" in prompt or "office" in prompt or "job" in prompt:
            return self._parse_daily_works()
        else:
            return None
        
    def _parse_shopping_items(self):
        return f"MATCH (u:User {{user_id: '{self.user_id}'}})-[:HAS_TASK]->(shopping)-[:CONTAINS]->(item:Item) RETURN item"
    
    def _parse_vacation_places(self):
        return f"MATCH (u:User {{user_id: '{self.user_id}'}})-[:HAS_TASK]->(travelling)-[:INCLUDES]->(place:Place) RETURN place"
    
    def _parse_daily_works(self):
        return f"MATCH (u:User {{user_id: '{self.user_id}'}})-[:HAS_TASK]->(work)-[:REQUIRED]->(office_work:Office_Work) RETURN office_work"

class ProductivityApp:
    
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth = (user, password))

    def close(self):
        self.driver.close()
  
    def add_user(self, name, age, user_id, password):
        with self.driver.session() as session:
            session.execute_write(self._create_user, name, age, user_id, password)

    @staticmethod
    def _create_user(tx, name, age, user_id, password):
        query = (
            "CREATE (user:User {name: $name, age: $age, user_id: $user_id, password: $password})"
            "CREATE (shopping_list:Task {type: 'Shopping'})"
            "CREATE (travel_destinations:Task {type: 'Travel'})"
            "CREATE (work:Task {type: 'Work'})"
            "CREATE (user)-[:HAS_TASK]->(shopping_list)"
            "CREATE (user)-[:HAS_TASK]->(travel_destinations)"
            "CREATE (user)-[:HAS_TASK]->(work)"
        )
        tx.run(query, name = name, age = age, user_id = user_id, password = password)

    def user_exists(self, user_id, password):
        with self.driver.session() as session:
            result = session.run(
                "MATCH (u:User {user_id: $user_id}) RETURN u.password AS password, u.name AS name, u.age AS age",
                user_id = user_id
            )
            response = result.single()
            if response is None:
                return 0, None, None
            if response["password"] != password:
                return 1, None, None     
            return 2, response["name"], response["age"]

    def add_shopping_item(self, user_id, item, quantity, unit):
        with self.driver.session() as session:
            session.execute_write(self._create_item, user_id, item, quantity, unit)
    
    def remove_shopping_item(self, user_id, item):
        with self.driver.session() as session:
            session.execute_write(self._remove_item, user_id, item)

    @staticmethod
    def _create_item(tx, user_id, item, quantity, unit):
        query = (
            "MATCH (user:User {user_id: $user_id})-[:HAS_TASK]->(connected_node) WHERE connected_node.type = 'Shopping'"
            "CREATE (item:Item {item_name: $item_name, quantity: $quantity, unit: $unit}) "
            "MERGE (connected_node)-[:CONTAINS]->(item) "
        )
        tx.run(query, user_id = user_id, item_name = item, quantity = quantity, unit = unit)
 
    @staticmethod
    def _remove_item(tx, user_id, item):
        query = (
            "MATCH (user:User {user_id: $user_id})-[:HAS_TASK]->(connected_node)-[:CONTAINS]->(item:Item {item_name: $item_name})"
            "DETACH DELETE item"
        )
        tx.run(query, user_id = user_id, item_name = item)

    def add_work(self, user_id, title, priority, deadline):
        with self.driver.session() as session:
            session.execute_write(self._create_work, user_id, title, priority, deadline)
    
    def remove_work(self, user_id, title):
        with self.driver.session() as session:
            session.execute_write(self._remove_work, user_id, title)

    @staticmethod
    def _create_work(tx, user_id, title, priority, deadline):
        query = (
            "MATCH (user:User {user_id: $user_id})-[:HAS_TASK]->(connected_node) WHERE connected_node.type = 'Work'"
            "CREATE (office_work:Office_Work {work_title: $work_title, priority: $priority, deadline: $deadline}) "
            "MERGE (connected_node)-[:REQUIRED]->(office_work) "
        )
        tx.run(query, user_id = user_id, work_title = title, priority = priority, deadline = deadline)

    @staticmethod
    def _remove_work(tx, user_id, title):
        query = (
            "MATCH (user:User {user_id: $user_id})-[:HAS_TASK]->(connected_node)-[:REQUIRED]->(office_work:Office_Work {work_title: $work_title})"
            "DETACH DELETE office_work"
        )
        tx.run(query, user_id = user_id, work_title = title)

    def add_place(self, user_id, city, country, estimated_cost):
        with self.driver.session() as session:
            session.execute_write(self._create_place, user_id, city, country, estimated_cost)

    def remove_place(self, user_id, city):
        with self.driver.session() as session:
            session.execute_write(self._remove_place, user_id, city)

    @staticmethod
    def _create_place(tx, user_id, city, country, estimated_cost):
        query = (
            "MATCH (user:User {user_id: $user_id})-[:HAS_TASK]->(connected_node) WHERE connected_node.type = 'Travel'"
            "CREATE (place:Place {city: $city, country: $country, estimated_cost: $estimated_cost}) "
            "MERGE (connected_node)-[:INCLUDES]->(place) "
        )
        tx.run(query, user_id = user_id, city = city, country = country, estimated_cost = estimated_cost)

    @staticmethod
    def _remove_place(tx, user_id, city):
        query = (
            "MATCH (user:User {user_id: $user_id})-[:HAS_TASK]->(connected_node)-[:INCLUDES]->(place:Place {city: $city})"
            "DETACH DELETE place"
        )
        tx.run(query, user_id = user_id, city = city)

    def answer_prompt(self, prompt):
        parser = QuestionParser(self, user_id)
        cypher_query = parser.parse_question(prompt)
        if not cypher_query:
            return "Sorry, I don't understand the question."
        
        results = self.driver.session().run(cypher_query).data()
        
        if not results:
            print("No record available")
        elif "item" in prompt or "shop" in prompt or "amount" in prompt: 
            if "amount" in prompt:
                for result in results:
                    if result["item"]["item_name"] in prompt:
                        print("Amount of " + result["item"]["item_name"] + " is " + str(result["item"]["quantity"]) + result["item"]["unit"])
            
            elif "all" in prompt or "items" in prompt:
                for result in results:
                    print(str(result["item"]["quantity"]) + result["item"]["unit"] + " of " + result["item"]["item_name"])
            
            else:
                for result in results:
                    if result["item"]["item_name"] in prompt:
                        print(str(result["item"]["quantity"]) + result["item"]["unit"] + " of " + result["item"]["item_name"])

        elif "spot" in prompt or "place" in prompt or "city" in prompt or "travelling" in prompt or "destination" in prompt or "vacation" in prompt:
            min_cost = float('inf')
            max_cost = 0
            
            if "cheapest" in prompt or "expensive" in prompt:
                if "cheapest" in prompt:
                    for result in results:
                        if min_cost > result["place"]["estimated_cost"]:
                            min_cost = result["place"]["estimated_cost"]
                            min_city = result["place"]["city"]
                    print("City " + min_city + " has minimum cost of " + str(min_cost))
                
                if "expensive" in prompt:
                    for result in results:
                        if max_cost < result["place"]["estimated_cost"]:
                            max_cost = result["place"]["estimated_cost"]
                            max_city = result["place"]["city"]
                    print("City " + max_city + " has maximum cost of " + str(max_cost)) 

            elif "all" in prompt or "spots" or "places" in prompt or "cities" in prompt:
                for result in results:
                    print("City " + result["place"]["city"] + " in "+ result["place"]["country"] + " with estimated cost of " + str(result["place"]["estimated_cost"]))
            else:
                for result in results:
                    if result["place"]["city"] in prompt:
                        print("City " + result["place"]["city"] + " in " + result["place"]["country"] + " with estimated cost of " + str(result["place"]["estimated_cost"]))
        elif "work" in prompt or "task" in prompt or "office" in prompt or "job" in prompt:
            if "priority" in prompt:
                if "high" in prompt or "medium" in prompt or "low" in prompt or "less" in prompt:
                    if "high" in prompt:
                        for result in results:
                            if result["office_work"]["priority"] == "HIGH":
                                print("Work " + result["office_work"]["work_title"] + " with deadline " + result["office_work"]["deadline"] + " has high priority ")
                    if "medium" in prompt:
                        for result in results:
                            if result["office_work"]["priority"] == "MEDIUM":
                                print("Work " + result["office_work"]["work_title"] + " with deadline " + result["office_work"]["deadline"] + " has medium priority ")
                    if "low" in prompt or "less" in prompt:
                        for result in results:
                            if result["office_work"]["priority"] == "LOW":
                                print("Work " + result["office_work"]["work_title"] + " with deadline " + result["office_work"]["deadline"] + " has low priority ")
                else:
                    for result in results:
                        print("Work " + result["office_work"]["work_title"] + " with deadline " + result["office_work"]["deadline"] + " has " + result["office_work"]["priority"] + " priority ")

            elif "deadline" in prompt:
                dd = int(prompt.split('-')[0][-2:])
                mm = int(prompt.split('-')[1])
                yy = int(prompt.split('-')[2][:4])
                deadline = datetime.datetime(yy, mm, dd)
                for result in results:
                    dd, mm, yy = map(int, result["office_work"]["deadline"].split('-'))
                    deadline_of_task = datetime.datetime(yy, mm, dd)
                    if deadline_of_task < deadline:
                        print("Work " + result["office_work"]["work_title"] + " with deadline " + result["office_work"]["deadline"] + " has " + result["office_work"]["priority"] + " priority")

            elif "all" or "works" in prompt:
                for result in results:
                    print("Work " + result["office_work"]["work_title"] + " with deadline " + result["office_work"]["deadline"] + " has " + result["office_work"]["priority"] + " priority ")


if __name__ == '__main__':
    
    
    password = "#" * 43
    connection_url = ".databases.neo4j.io:7687"

    app = ProductivityApp(f"bolt+s://{connection_url}", "neo4j", password)
    print("""
   _____          _____ _    _ ______        _____ _______ 
  / ____|   /\   / ____| |  | |  ____|      |_   _|__   __|
 | |       /  \ | |    | |__| | |__           | |    | |   
 | |      / /\ \| |    |  __  |  __|          | |    | |   
 | |____ / ____ | |____| |  | | |____        _| |_   | |   
  \_____/_/    \_\_____|_|  |_|______|      |_____|  |_|   
         
         """)
    
    start = int(input("Enter \n1. To register \n2. To log in\n"))
    
    if start == 1:
        print("---------------------------Register-------------------------")
        name = input("Enter your name: ")
        age = int(input("Enter your age: "))
        user_id = input("Enter your e-mail id: ")
        password = input("Enter password: ")
        app.add_user(name, age, user_id, password)
    
    elif start == 2:
        print("----------------------------Log in--------------------------")
        user_id = input("Enter your e-mail id: ")
        password = input("Enter password: ")
        signal, name, age = app.user_exists(user_id, password)

        if signal == 0:
            print("E-mail id does not exist please register: ")
            name = input("Enter your name: ")
            age = int(input("Enter your age: "))
            user_id = input("Enter your e-mail id: ")
            apassword = input("Enter password: ")
            app.add_user(name, age, user_id, password)
        
        elif signal == 1:
            print("Incorrect password")
            while signal != 2:
                password = input("Try again, Enter password: ")
                signal, name, age = app.user_exists(user_id, password)
            print(f"Welcome back {name}")

        elif signal == 2:
            print(f"Welcome back {name}")
    print("--------------------Continue where you left-----------------")
    print("Queries \n1. To edit a shopping list \n2. To edit work deadlines \n3. To edit vacation plans \n4. To chat with CACHE IT \n5. To exit")
    
    while True:
        
        query = int(input("Enter choice: "))
        
        if query == 1:
            prompt = (input("What would you like to edit in the shopping list? ")).lower()
            if "add" in prompt or "insert" in prompt:
                item = input("What item? ")
                quantity = int(input("Quantity of the item? "))
                unit = input("Units of measurement? ")
                app.add_shopping_item(user_id, item, quantity, unit)
            elif "delete" in prompt or "remove" in prompt:
                item = input("What item: ")
                app.remove_shopping_item(user_id, item)
            else:
                print("Sorry I could not understand, could you please repeat")

        elif query == 2:
            prompt = (input("What would you like to edit in the works list? ")).lower()
            if "add" in prompt or "insert" in prompt:
                title = input("What is the work title? ")
                deadline = input("What is the deadline of the work? ")
                priority = input("Priority of the work as HIGH, MEDIUM, LOW? ")
                app.add_work(user_id, title, priority, deadline)
            elif "delete" in prompt or "remove" in prompt:
                title = input("What is the work title? ")
                app.remove_work(user_id, title)
            else:
                print("Sorry I could not understand, could you please repeat")

        elif query == 3:
            prompt = (input("What would you like to edit in the travelling places list? ")).lower()
            if "add" in prompt or "insert" in prompt:
                city = input("What is the city name? ")
                country = input("What is the country? ")
                estimated_cost = float(input("What is the estimated cost of travel? "))
                app.add_place(user_id, city, country, estimated_cost)
            elif "delete" in prompt or "remove" in prompt:
                city = input("What is the city name? ")
                app.remove_place(user_id, city)

        elif query == 4:
            print("Enter exit to stop the chat")
            while True:
                prompt = (input("What do you want to know: ")).lower()
                if prompt == "exit":
                    break
                app.answer_prompt(prompt)
        else:
            break
    
    app.close()
