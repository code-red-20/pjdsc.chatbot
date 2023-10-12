from dotenv import load_dotenv
from flask import Flask, request
from llama_index import GPTVectorStoreIndex, SimpleDirectoryReader, LLMPredictor, ServiceContext, StorageContext, load_index_from_storage
from langchain.chat_models import ChatOpenAI
import os
import openai
import requests

app = Flask(__name__)

load_dotenv()

# API key stored privately
openai.api_key = os.getenv("OPENAI_API_KEY")
# Page access token from the Facebook Developer console
PAGE_ACCESS_TOKEN = os.getenv("PAGE_TOKEN")
# API Key for Facebook Messenger
API="https://graph.facebook.com/v16.0/me/messages?access_token="+PAGE_ACCESS_TOKEN

def construct_index(directory_path):

    # Set the number of output tokens
    num_outputs = 256

    _llm_predictor = LLMPredictor(llm=ChatOpenAI(temperature=0.5, model_name="gpt-3.5-turbo", max_tokens=num_outputs))
    service_context = ServiceContext.from_defaults(llm_predictor=_llm_predictor)
    docs = SimpleDirectoryReader(directory_path).load_data()
    index = GPTVectorStoreIndex.from_documents(docs, service_context=service_context)
    
    # Set the directory in which the indexes will be stored
    index.storage_context.persist(persist_dir="indexes")

    return index

def chatbot(input_text):
    
    # Rebuild the storage context
    storage_context = StorageContext.from_defaults(persist_dir="indexes")
    
    # Load the indexes from directory using storage_context 
    query_engne = load_index_from_storage(storage_context).as_query_engine()
    
    # Query the input and returns a response type
    response = query_engne.query(input_text)
    
    # Return the response of the chatbot
    return response.response

@app.route('/', methods=['GET'])
def verify():
    # Verify the webhook subscription with Facebook Messenger
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == "pjdsc2023":
            return "Verification token mismatch"
        
        # Return the challenge string if the verify token specified in the webhook matches the token set above
        return request.args.get('hub.challenge')
    
    # Return a message if the specified mode does not match the GET request mode
    return "Hello world"

# Manages webhook function for receiving user input and providing ChatGPT response
@app.route("/", methods=['POST'])
def fbwebhook():
    data = request.get_json()
    try:
        if data['entry'][0]['messaging'][0]['sender']['id']:
            message = data['entry'][0]['messaging'][0]['message']
            sender_id = data['entry'][0]['messaging'][0]['sender']['id']
            chat_gpt_input=message['text']
            print("User: ", chat_gpt_input)
            chatbot_res = chatbot(chat_gpt_input)
            print("ChatGPT Response: ",chatbot_res)
            response = {
                'recipient': {'id': sender_id},
                'message': {'text': chatbot_res}
            }
            requests.post(API, json=response)
    except Exception as e:
        print(e)
        pass
    return '200 OK HTTPS.'

# Run the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False, port=5000)