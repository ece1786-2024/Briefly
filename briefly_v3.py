import openai
import pandas as pd

def agent_turn(system_prompt, conversation_history, article_content, model_nm="gpt-3.5-turbo", num_prev_msgs=1):
    """
    Generates a response from an agent, only aware of the article content and the last 'num_prev_msgs' messages.
    """
    # Build the messages list starting with the system prompt
    # Include the article content as a user message at the beginning
    article_message = {"role": "user", "content": article_content}
    messages = [{"role": "system", "content": system_prompt}, article_message] + conversation_history[-num_prev_msgs:]

    response = openai.ChatCompletion.create(
        model=model_nm,
        messages=messages
    )

    assistant_reply = response['choices'][0]['message']

    # Append assistant's reply to the conversation history
    conversation_history.append(assistant_reply)

    return assistant_reply['content']

def extract_known_information(final_summary, curr_knowledge, article_content, model_nm="gpt-3.5-turbo"):
    """
    Use the Personalization Agent to identify known information in the final summary.
    """
    # Initialize conversation history with the final summary
    conversation_history = [{"role": "assistant", "content": final_summary}]

    # Ask the Personalization Agent to identify known topics based on the summary
    extraction_prompt = (
        f"Known information from the user includes:\n{curr_knowledge}\n\n"
        "Please identify any new topics or details in the summary that are not part of the known information based on user's interests which is indicated in curr_knowledge."
        "List keywords separated by semicolons and be consice."
        "In your response, just list the keywords."
    )

    # Run the Personalization Agent to extract known information
    known_info_response = agent_turn(extraction_prompt, conversation_history, article_content, model_nm)
    print(f"Extracted Known Information:\n{known_info_response}\n")

    # Return the known information extracted by the Personalization Agent
    return known_info_response

def update_personalization_prompt(original_prompt, known_information):
    """
    Update the Personalization Agent's prompt with the known information.
    """
    if pd.isna(known_information) or not known_information.strip():
        updated_prompt = original_prompt
    else:
        updated_prompt = (
            f"{original_prompt}\n\n"
            f"Known information from the user includes:\n{known_information}\n\n"
            "Please focus your feedback on any additional details or gaps not covered by this information."
        )
    return updated_prompt

def update_agent_knowledge(df_agent, agent_id, known_info):
    """
    Update the knowledge column for the specified agent in df_agent.
    """
    # Retrieve the current knowledge, handling NaN values
    current_knowledge = df_agent.loc[df_agent['agent_id'] == agent_id, 'knowledge'].values[0]
    
    # If current_knowledge is NaN, set it to an empty string
    if pd.isna(current_knowledge):
        current_knowledge = ""

    # Append known information to the existing knowledge
    updated_knowledge = current_knowledge + "; " + known_info if current_knowledge else known_info
    df_agent.loc[df_agent['agent_id'] == agent_id, 'knowledge'] = updated_knowledge

def agent_conversation(df_article, articledb, num_iterations, summary_agent, persona, model_nm="gpt-3.5-turbo"):
    # Load agent prompts and knowledge from the original CSV file
    df_agent = pd.read_csv('data/agents.csv', encoding='ISO-8859-1')

    # Get original prompts for each agent
    summary_prompt = df_agent.loc[df_agent['agent_id'] == summary_agent, 'prompt'].values[0]
    persona_prompt = df_agent.loc[df_agent['agent_id'] == persona, 'prompt'].values[0]

    ids = 0
    data_feedback = []

    # Get current knowledge for the personalization agent
    curr_knowledge = df_agent.loc[df_agent['agent_id'] == persona, 'knowledge'].values[0]

    for index, article in df_article.iterrows():
        print(f"\nProcessing Article ID: {article['article_id']}")

        # Initialize conversation history
        conversation_history = []

        # Create the article content
        article_content = (
            f"Article ID: {article['article_id']}\n"
            f"Date: {article['Date of Article']}\n"
            f"Title: {article['Title']}\n"
            f"Body: {article['Body']}"
        )

        # Create the user message with the article content
        user_message = {
            "role": "user",
            "content": article_content
        }
        conversation_history.append(user_message)

        for i in range(num_iterations):
            print(f"\n--- Iteration {i+1} ---")

            # Summary Agent generates a summary using the original prompt
            summary_response = agent_turn(summary_prompt, conversation_history, article_content, model_nm, num_prev_msgs=1)
            print(f"Summary Agent Response:\n{summary_response}\n")
            # Append the assistant's reply to the conversation history
            conversation_history.append({
                "role": "assistant",
                "content": summary_response
            })

            # Update the Personalization Agent prompt with current knowledge
            updated_persona_prompt = update_personalization_prompt(persona_prompt, curr_knowledge)

            # Personalization Agent provides feedback
            feedback_response = agent_turn(updated_persona_prompt, conversation_history, article_content, model_nm, num_prev_msgs=2)
            print(f"Personalization Agent Feedback:\n{feedback_response}\n")
            # Append the assistant's reply to the conversation history
            conversation_history.append({
                "role": "assistant",
                "content": feedback_response
            })

            # Keep accumulating feedback data
            data_feedback.append([
                ids, 
                persona, 
                article['article_id'], 
                article['Title'],
                summary_response, 
                feedback_response
            ])

            ids += 1

        # Final summary using the conversation history
        summary_response = agent_turn(summary_prompt, conversation_history, article_content, model_nm, num_prev_msgs=1)
        print(f"Final Summary Agent Response:\n{summary_response}\n")
        # Append the assistant's reply to the conversation history
        conversation_history.append({
            "role": "assistant",
            "content": summary_response
        })

        
        # Extract known information from the final summary using the Personalization Agent
        known_info_response = extract_known_information(summary_response, curr_knowledge, article_content, model_nm)

        # Update the knowledge base with final known information
        update_agent_knowledge(df_agent, persona, known_info_response)


        data_feedback.append([
            ids,
            persona,
            article['article_id'],
            article['Title'],
            summary_response,
            "Extracted Known Information: \n" + known_info_response
        ])

    # Convert the 2D list to a DataFrame
    columns_feedback = ['conversation_id', 'persona_id', 'article_id', 'Title', 'summary', 'feedback']
    df_feedback = pd.DataFrame(data_feedback, columns=columns_feedback)
    df_feedback.to_csv(f'results/feedback_{summary_agent}_{persona}_{articledb}.csv', index=False)

    # Overwrite the original df_agent with updated knowledge
    df_agent.to_csv('data/agents.csv', index=False, encoding='ISO-8859-1')

    return df_feedback[df_feedback['conversation_id'] == ids]["summary"], df_feedback

if __name__ == "__main__":
    with open('../open_ai_api_key.txt', 'r') as file:
        api_key = file.readline().strip()
    openai.api_key = api_key

    df_article_tech = pd.read_csv('data/tech_articles.csv')
    df_article_tech = df_article_tech.rename(columns={'ID': 'article_id'})

    EV_article = df_article_tech[df_article_tech["Title"] == "Opinion: Canada must look beyond EV tariffs and force China to play by global trade rules"]#"Opinion: Chinese EVs aren’t just an economic threat – they are a security risk"]#"Would you buy an affordable EV made in China?"]

    final_summaries, df_feedback = agent_conversation(
        df_article=EV_article,
        articledb="Ev_article_test_knowledge_extend",
        num_iterations=3,
        summary_agent='sa9',
        persona='jc7',
        model_nm="gpt-3.5-turbo"
    )
