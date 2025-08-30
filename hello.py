from prefect import flow, tags

@flow(log_prints=True)
def hello(name: str = "Marvin") -> None:
    print(f"Hello, {name}!")

if __name__ == "__main__":
    with tags("test"):
        hello()

        hello("Jason")

        crew = ["Marvin", "Jason", "Alice", "Bob"]
        for name in crew:
            hello(name)

