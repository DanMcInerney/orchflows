def check(c):
    path = c.stage() / "answer.txt"
    c.require(path.is_file() and path.read_text().strip() == "42", "Correct arithmetic output", "stages/target/workspace/answer.txt")
