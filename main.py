import openai
import re

# Replace with your OpenAI API key
openai.api_key = 'sk-hK6R3YBqSo1uP8uqnv29JqcmVqP76TTxlvVL1qDePTT3BlbkFJW6t0tVuTyM4ts9S6COIi1_vBMp4XU3q7OM75SQnJsA'


def create_summary(summarized_article, knowledge_base, instruction):
    """
    This function takes a summarized article and a knowledge base, then prompts the model
    to modify the summary based on the given knowledge using the chat API.
    """
    # OpenAI GPT prompt to modify the existing summary using prior knowledge
    knowledge_list = ', '.join(knowledge_base)  # Join knowledge base items into a comma-separated string
    prompt = f"""
    I am already up to date about {knowledge_list}. 
    Please create a personalized summary of the article.
    You may omit information that may already be related to this knowledge that I already have. 
    Make sure to still report any new information from the article. 

    Here is a further instruction:
    {instruction}

    Fulfill this instruction if the information needed to fulfill it is within the article.

    Summarized Article:
    {summarized_article}

    New Modified Summary:
    """

    try:
        # Make the API call to generate the modified summary using GPT-3.5's chat endpoint
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Using GPT-3.5 model
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,  # Allow room for a detailed summary
            temperature=0.5,  # Adjust creativity (0.0-1.0)
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )
        # Extract the new modified summary from the response
        new_summary = response['choices'][0]['message']['content'].strip()
        return new_summary
    except Exception as e:
        return f"Error modifying the summary: {e}"


def generate_instruction(knowledge_base, summary, specific_mode):
    

    if specific_mode:
        # If there are matching topics, construct the prompt based on those matches
        print("specific_mode")
        prompt = (
            f"Given the following knowledge base:\n"
            f"{', '.join(knowledge_base)},\n"
            f"and the following article summary:\n"
            f"{summary}\n"
            "Generate an instruction that will make the article more specific or relevant to what is in knowledge base."
        )


    else:
        # If there are no matching topics, focus on missing topics
        print("other mode")
        prompt = (
            f"Given the following knowledge base:\n"
            f"{', '.join(knowledge_base)},\n"
            f"and the following article summary:\n"
            f"{summary}\n"
            "Generate an instruction that will make the summary expand more on things that may be important from the article."
        )
    
    # Call the OpenAI API to generate a response using the chat completion endpoint
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # Using the cheaper model
        messages=[
            {"role": "system", "content": "You are an agent that generates instructions or questions to make an article more relevant to specific interests."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=50,  # Increased token limit to allow for more detailed suggestions
        temperature=1
    )
    
    # Extract the generated text from the response
    suggestion = response['choices'][0]['message']['content'].strip()
    return suggestion


# Example usage
if __name__ == "__main__":

    with open("article_sports_1.txt", "r") as file:
        article_text = file.read() 


    #print(article_text)
    
    # Example of previous knowledge you want to incorporate
    knowledge_base = []

    try:
        with open("knowledge_base.txt", "r") as kb_file:
            knowledge_base = [line.strip() for line in kb_file.readlines()]
    except FileNotFoundError:
        print("knowledge_base.txt not found. Starting with an empty knowledge base.")
    

    print("Initial Knowledge Base: \n", knowledge_base)
    
    zero_shot_summary = create_summary(article_text, knowledge_base, "no special instructions")
    print("Original Zero Shot Summary:")
    print(zero_shot_summary)
    print("\n")


    ## Example of previous knowledge you want to incorporate

    for i in range(3):
        instruction = generate_instruction(knowledge_base, zero_shot_summary, specific_mode=0)
        print("Instruction: ", instruction)
        
        new_summary = create_summary(article_text, knowledge_base, instruction)

        print("New summary after an instruction: ")
        print(new_summary)
        print("\n")

    #test adding something to the knowledge base
    #knowledge_base.append('Jonathan Mingo trade')

    # Save the knowledge base to a text file
    with open("knowledge_base.txt", "w") as kb_file:
        for item in knowledge_base:
            kb_file.write(item + "\n")
