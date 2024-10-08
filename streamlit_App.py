import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set Streamlit page configuration
st.set_page_config(page_title="Document Genie", layout="wide")

# Display the app introduction
st.markdown("""
## Document Genie: Get instant insights from your Documents

This chatbot is built using the Retrieval-Augmented Generation (RAG) framework, leveraging Google's Generative AI model Gemini-PRO. It processes uploaded PDF documents by breaking them down into manageable chunks, creates a searchable vector store, and generates accurate answers to user queries. This advanced approach ensures high-quality, contextually relevant responses for an efficient and effective user experience.

### How It Works

Follow these simple steps to interact with the chatbot:

1. **Enter Your API Key**: You'll need a Google API key for the chatbot to access Google's Generative AI models. Obtain your API key from https://makersuite.google.com/app/apikey.

2. **Upload Your Documents**: The system accepts multiple PDF files at once, analyzing the content to provide comprehensive insights.

3. **Ask a Question**: After processing the documents, ask any question related to the content of your uploaded documents for a precise answer.
""")

# API Key input field
api_key = st.text_input("Enter your Google API Key:",
                        type="password", key="api_key_input")

# Function to extract text from PDF files


def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text() or ""  # Handle potential NoneType
    return text

# Function to split text into chunks


def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=10000, chunk_overlap=1000)
    chunks = text_splitter.split_text(text)
    return chunks

# Function to create and save vector store


def get_vector_store(text_chunks, api_key):
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001", google_api_key=api_key)
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_store.save_local("faiss_index")

# Function to get conversational chain for question answering


def get_conversational_chain(api_key):
    prompt_template = """
    Answer the question as detailed as possible from the provided context. If the answer is not in
    the provided context, say, "answer is not available in the context." Do not provide a wrong answer.\n\n
    Context:\n {context}\n
    Question:\n {question}\n

    Answer:
    """
    model = ChatGoogleGenerativeAI(
        model="gemini-pro", temperature=0.3, google_api_key=api_key)
    prompt = PromptTemplate(template=prompt_template,
                            input_variables=["context", "question"])
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
    return chain

# Function to handle user input and generate response


def user_input(user_question, api_key):
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001", google_api_key=api_key)
    try:
        logger.info("Loading vector store...")
        # Allow dangerous deserialization as per the requirement
        new_db = FAISS.load_local(
            "faiss_index", embeddings, allow_dangerous_deserialization=True)
        logger.info("Vector store loaded successfully.")
    except FileNotFoundError:
        st.error(
            "Vector store file not found. Please upload and process your PDF files.")
        return
    except ValueError as e:
        st.error(f"Error loading vector store: {e}")
        logger.error(f"Error loading vector store: {e}")
        return

    docs = new_db.similarity_search(user_question)
    chain = get_conversational_chain(api_key)
    response = chain(
        {"input_documents": docs, "question": user_question}, return_only_outputs=True)
    st.write("Reply: ", response.get("output_text", "No response generated."))

# Main function to run the Streamlit app


def main():
    st.header("AI Clone Chatbot 💁")

    user_question = st.text_input(
        "Ask a Question from the PDF Files", key="user_question")

    if user_question and api_key:  # Ensure API key and user question are provided
        user_input(user_question, api_key)

    with st.sidebar:
        st.title("Menu:")
        pdf_docs = st.file_uploader(
            "Upload your PDF Files and Click on the Submit & Process Button",
            accept_multiple_files=True,
            key="pdf_uploader"
        )
        # Check if API key is provided before processing
        if st.button("Submit & Process", key="process_button") and api_key:
            if pdf_docs:  # Check if PDF files are uploaded
                with st.spinner("Processing..."):
                    raw_text = get_pdf_text(pdf_docs)
                    text_chunks = get_text_chunks(raw_text)
                    get_vector_store(text_chunks, api_key)
                    st.success(
                        "Processing complete. You can now ask questions.")
            else:
                st.error("Please upload at least one PDF file.")


if __name__ == "__main__":
    main()
