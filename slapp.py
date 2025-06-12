import streamlit as st
from langchain_openai import ChatOpenAI 
from langchain_core.prompts import PromptTemplate
from langchain.chains import LLMChain
import os
import json
import logging
import base64

logging.basicConfig(level=logging.INFO)

st.set_page_config(page_title="Call Flow")

# --- Initialize Session State ---
if "current_step_id" not in st.session_state:
    st.session_state.current_step_id = "0-start"
if "ai_chat_open" not in st.session_state:
    st.session_state.ai_chat_open = False
if "call_flow" not in st.session_state:
    st.session_state.call_flow = None
if "selected_language" not in st.session_state:
    st.session_state.selected_language = None

# --- Function to load local CSS ---
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("style.css")

# --- Header with Logo and Mode Toggle ---
try:
    import os 
    import base64

    def get_base64(file_path):
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode()

    logo_path = "images/logo.svg"

    col1, col2 = st.columns([1, 1])

    with col1:
        if os.path.exists(logo_path):
            base64_logo = get_base64(logo_path)
            st.markdown(
                f'<img src="data:image/svg+xml;base64,{base64_logo}" alt="Logo">',
                unsafe_allow_html=True
            )
        else:
            st.error(f"Logo not found at {logo_path}")

    with col2:
        # Toggle button
        button_label = "AI Chat Mode" if not st.session_state.ai_chat_open else "Call Flow Mode"
        if st.button(button_label, key="nav_button-toggle"):
            st.session_state.ai_chat_open = not st.session_state.ai_chat_open
            st.rerun()

except FileNotFoundError:
    st.error(f"Error: {logo_path} not found. Ensure it's in the 'images' directory.")
except Exception as e:
    st.error(f"An error occurred: {e}")


# --- Function to load the call flow script based on language ---
def load_call_flow(language):
    """Loads the call flow script from a JSON file based on the selected language."""
    filename_map = {
        "UK": "call_flow_en.json",
        "ES": "call_flow_es.json",
        "FR": "call_flow_fr.json",
        "IT": "call_flow_it.json",
        "DE": "call_flow_de.json",
        "PT": "call_flow_pt.json"
    }
    filename = filename_map.get(language)
    if not filename:
        st.error(f"Error: No JSON file mapping found for language: {language}")
        logging.error(f"No JSON file mapping found for language: {language}")
        return None
    filepath = os.path.join(".", filename)
    logging.info(f"Attempting to load call flow from: {filepath}")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            logging.info(f"Successfully loaded JSON from: {filepath}")
            logging.debug(f"Loaded JSON data: {data}")
            return data
    except FileNotFoundError:
        st.error(f"Error: {filename} not found in the current directory.")
        logging.error(f"File not found: {filepath}")
        return None
    except json.JSONDecodeError as e:
        st.error(f"Error: Could not decode JSON from {filename}. Error: {e}")
        logging.error(f"JSONDecodeError in {filepath}: {e}")
        return None

if not st.session_state.ai_chat_open:
    st.markdown("<h2 class='main-title'>Interactive Script</h2>", unsafe_allow_html=True)

    if st.session_state.current_step_id == "0-start":
        if st.button("New Interaction", key="button-main"):
            st.session_state.current_step_id = "1-language"
            st.rerun()
    elif st.session_state.current_step_id == "1-language":
        language_options = ["UK", "ES", "FR", "IT", "DE", "PT"]
        st.write("Select Language:")
        language_selection = st.columns(len(language_options))
        for i, lang in enumerate(language_options):
            if language_selection[i].button(lang, key=f"lang_button_{lang.lower()}"):
                st.session_state.selected_language = lang
                st.session_state.call_flow = load_call_flow(lang)
                if st.session_state.call_flow and "steps" in st.session_state.call_flow:
                    st.session_state.current_step_id = st.session_state.call_flow["steps"][0]["id"]
                else:
                    st.error("Error: No 'steps' found in the loaded JSON or loading failed.")
                    st.session_state.current_step_id = None
                st.rerun()
        
        # --- Navigation buttons for 1-language step ---
        nav_cols = st.columns(2)
        with nav_cols[0]:
            if st.button("Back", key="back_button"):
                st.session_state.current_step_id = "0-start"
                st.session_state.call_flow = None
                st.session_state.selected_language = None
                st.rerun()
        with nav_cols[1]:
            pass # No 'Next' button on this screen

    elif st.session_state.call_flow and st.session_state.current_step_id:
        call_flow = st.session_state.call_flow
        current_step_id = st.session_state.current_step_id
        current_step = None
        for step in call_flow.get("steps", []): # Use .get() to handle potential missing 'steps'
            if step["id"] == current_step_id:
                current_step = step
                break

        if current_step:
            if "elements" in current_step and isinstance(current_step["elements"], list):
                for element_config in current_step["elements"]:
                    element_type = element_config.get("ui_type")

                    if element_type == "text_display":
                        if "content" in element_config and element_config["content"]:
                            st.write(element_config["content"])

                    elif element_type == "script_display":
                        if "script_text" in element_config and element_config["script_text"]:
                            st.markdown(
                                f'<div class="agent-script">{element_config["script_text"]}</div>',
                                unsafe_allow_html=True
                            )

                    elif element_type == "text_input":
                        label = element_config.get("label", "Enter text:")
                        input_widget_key = element_config.get("key", f"{current_step['id']}_{element_type}_{element_config.get('id', '')}_widget")
                        st.text_input(label, key=input_widget_key)
                        # Streamlit automatically stores the input value in st.session_state[input_widget_key]

                    elif element_type == "buttons":
                        label = element_config.get("label", "")
                        if label:
                            st.write(label)
                        options_data = element_config.get("options", [])
                        cols = st.columns(len(options_data))
                        for i, option_data in enumerate(options_data):
                            with cols[i]:
                                button_label = option_data.get("label", "Button")
                                button_value = option_data.get("value", f"btn_val_{i}")
                                button_widget_key = f"button_element_{current_step['id']}_{button_value}"
                                if st.button(button_label, key=button_widget_key):
                                    next_step_id = option_data.get("next", current_step.get("next"))
                                    st.session_state.current_step_id = next_step_id
                                    st.rerun()
                                    break # Exit loop after button click

                    elif element_type == "checkboxes":
                        label = element_config.get("label", "")
                        if label:
                            st.write(label)
                        options_data = element_config.get("options", [])

                        storage_key_for_checkbox_group = element_config.get("key", f"{current_step['id']}_{element_type}_selected_group")

                        if storage_key_for_checkbox_group not in st.session_state:
                            st.session_state[storage_key_for_checkbox_group] = []

                        current_selected_options = []
                        for option_item in options_data:
                            option_text = option_item.get("label", option_item) if isinstance(option_item, dict) else option_item
                            checkbox_widget_key = f"checkbox_widget_{current_step['id']}_{option_text}_{storage_key_for_checkbox_group}"

                            is_checked_initially = option_text in st.session_state[storage_key_for_checkbox_group]

                            if st.checkbox(option_text, key=checkbox_widget_key, value=is_checked_initially):
                                current_selected_options.append(option_text)
                        
                        st.session_state[storage_key_for_checkbox_group] = current_selected_options

                    elif element_type == "text_area":
                        label = element_config.get("label", "Enter text:")
                        text_area_widget_key = element_config.get("key", f"text_area_widget_{current_step['id']}_{element_type}")
                        st.text_area(label, key=text_area_widget_key)
                        # Streamlit automatically stores the text area content in st.session_state[text_area_widget_key]

                    elif element_type == "button":
                        button_label = element_config.get("label", "Action")
                        button_widget_key = element_config.get("key", f"action_button_element_{current_step['id']}_{element_type}")
                        if st.button(button_label, key=button_widget_key):
                            next_step_id = element_config.get("next", current_step.get("next"))
                            st.session_state.current_step_id = next_step_id
                            st.rerun()
            else:
                # Fallback for steps that might not explicitly have an "elements" list but still need content.
                if "content" in current_step and current_step["content"]:
                    st.write(current_step["content"])
                if "script_text" in current_step and current_step["script_text"]:
                    st.markdown(
                        f'<div class="agent-script">{current_step["script_text"]}</div>',
                        unsafe_allow_html=True
                    )

            # --- Navigation Buttons (Back and Next) ---
            show_standard_nav_buttons = True 

            if show_standard_nav_buttons:
                nav_cols = st.columns(2)

                # Back Button (always in the first column if available)
                with nav_cols[0]:
                    if "back" in current_step:
                        if st.button("Back", key=f"back_button_{current_step_id}"):
                            st.session_state.current_step_id = current_step["back"]
                            st.rerun()

                # Next Button (only in the second column if available)
                with nav_cols[1]:
                    if "next" in current_step:
                        if st.button("Next", key=f"next_button_{current_step_id}"):
                            st.session_state.current_step_id = current_step["next"]
                            st.rerun()
        else:
            st.write("Error: Current step not found in loaded call flow.")

else:
    # AI Chat Mode
    st.markdown("<h2 class='main-title'>AI Assistant</h2>", unsafe_allow_html=True)

    # Initialize Deepseek LLM via OpenRouter
    if "llm" not in st.session_state:
        # Get Deepseek API key from Streamlit secrets
        deepseek_api_key = st.secrets["deepseek_api_key"] 
        
        st.session_state.llm = ChatOpenAI(
            openai_api_base="https://openrouter.ai/api/v1",
            openai_api_key=deepseek_api_key,
            model_name="deepseek/deepseek-r1:free", 
            temperature=0.0
        )
    llm = st.session_state.llm

    category_options = ["UK T&Cs BD AD", "UK T&Cs BD AD THEFT MOBILE", "UK T&Cs BD AD THEFT NON-MOBILE"]
    category = st.selectbox("Select Category:", category_options)
    user_question = st.text_area("Ask your question:", key="user_input")
    submit_button = st.button("Submit", key="button-main")

    if submit_button and user_question:
        file_path = ""
        file_name_prefix = "kb"
        base_path = "." # Ensure this path is correct for your system

        if category == "UK T&Cs BD AD":
            file_path = os.path.join(base_path, f"01-{file_name_prefix}-uk-tcs-bd-ad.txt")
        elif category == "UK T&Cs BD AD THEFT MOBILE":
            file_path = os.path.join(base_path, f"02-{file_name_prefix}-uk-tcs-bd-ad-theft-mobile.txt")
        elif category == "UK T&Cs BD AD THEFT NON-MOBILE":
            file_path = os.path.join(base_path, f"03-{file_name_prefix}-uk-tcs-bd-ad-theft-non-mobile.txt")
        else:
            st.error(f"Invalid category: {category}")
            st.stop()

        document_content = ""
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    document_content = f.read()
            except Exception as e:
                document_content = f"Error reading file: {e}"
                st.error(document_content)
        else:
            document_content = f"Category file not found: {file_path}"
            st.error(document_content)

        prompt_template = f"""
        You are a search engine that finds answers in a knowledge base.

        **Instructions:**

        1.  **Search Knowledge Base:** Carefully read the knowledge base below to find the answer to this question: "{user_question}".

            **Knowledge Base:**
            {document_content}

        2.  **Generate Answer:**
            * **If a potential answer is found:** Provide a straight-to-the-point short answer using ONLY information that is available on the knowledge base. IMPORTANT: After adding your straight-to-the-point short answer, please add separate paragraph, starting with "<b>Quote:</b>" then insert the most concise direct quote from the knowledge base to indicate the source for the information provided.
            * **If a potential answer is NOT found:** Respond exactly with this sentence: "Unfortunately, I'm unable to provide you a response to your question."
        """
        prompt = PromptTemplate(template=prompt_template, input_variables=[])
        chain = LLMChain(llm=llm, prompt=prompt)

        with st.spinner("Generating response..."):
            try:
                final_response = chain.run({})

                with st.container(key="ai-response-container"):
                    st.header("AI Answer", divider=True)
                    st.markdown(f"<p class='ai-answer-string'>{final_response.strip()}</p>", unsafe_allow_html=True)

            except Exception as e:
                st.error(f"Error during Deepseek API call: {e}")