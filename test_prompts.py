from src.core.prompts import prompt_manager
import os

def test_prompts():
    print("Testing HR Prompt Loading...")
    try:
        prompt = prompt_manager.get_formatted_prompt(
            domain="hr",
            template_name="manager_sop",
            context_str="SOP: Leave Policy states 20 days annual leave.",
            query_str="How many annual leave days?"
        )
        print("HR Prompt Loaded Successfully:\n", prompt)
    except Exception as e:
        print("Failed to load HR Prompt:", e)

    print("\nTesting Missing Prompt...")
    try:
        prompt_manager.load_prompt("hr", "missing_file")
    except FileNotFoundError:
        print("Correctly caught missing file error.")
    except Exception as e:
        print("Unexpected error:", e)

if __name__ == "__main__":
    test_prompts()
