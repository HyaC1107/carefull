from config.settings import TEST_MODE


def dispense_medicine(user):
    if TEST_MODE:
        print(f"[TEST DISPENSE] {user} medicine dispense simulated")
        return

    print(f"[DISPENSE] start for {user}")
    # TODO: Raspberry Pi GPIO motor control goes here.
    print(f"[DISPENSE DONE] {user}")
