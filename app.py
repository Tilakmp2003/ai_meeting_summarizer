from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import google.generativeai as genai
import re # For parsing

app = Flask(__name__)
CORS(app) # Initialize CORS for all routes

# Load environment variables from .env file
load_dotenv()

# Configure the Gemini API key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("Error: GOOGLE_API_KEY not found in .env file. Please set it.")
    # You might want to raise an exception or exit if the key is critical
else:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
    except Exception as e:
        print(f"Error configuring Google Generative AI: {e}")
        # Handle configuration error, e.g., by disabling AI features or exiting

def parse_llm_response(response_text):
    """
    Parses the LLM's text response to extract summary, decisions, and action items.
    Assumes the LLM follows the requested format with headings.
    """
    summary = "Could not parse summary."
    decisions = []
    action_items = []

    try:
        # Normalize line endings and split by common section headers
        # Using case-insensitive regex for robustness
        summary_match = re.search(r"Summary:(.*?)Key Decisions:", response_text, re.IGNORECASE | re.DOTALL)
        decisions_match = re.search(r"Key Decisions:(.*?)Action Items:", response_text, re.IGNORECASE | re.DOTALL)
        action_items_match = re.search(r"Action Items:(.*)", response_text, re.IGNORECASE | re.DOTALL)

        if summary_match:
            summary_text = summary_match.group(1).strip()
            if summary_text.lower() != "none":
                summary = summary_text
            else:
                summary = "None provided."


        if decisions_match:
            decisions_text = decisions_match.group(1).strip()
            if decisions_text.lower() != "none":
                decisions = [d.strip() for d in decisions_text.split('\n') if d.strip().startswith(("*", "-")) or d.strip()]
                decisions = [re.sub(r"^\s*[\*\-]\s*", "", d).strip() for d in decisions if d.strip()] # Remove bullets and trim
                decisions = [d for d in decisions if d] # Filter out empty strings
            if not decisions and decisions_text.lower() != "none" and decisions_text: # Handle cases where "None" is not used but content is there
                 decisions = [decisions_text] if decisions_text else []


        if action_items_match:
            action_items_text = action_items_match.group(1).strip()
            if action_items_text.lower() != "none":
                action_items = [ai.strip() for ai in action_items_text.split('\n') if ai.strip().startswith(("*", "-")) or ai.strip()]
                action_items = [re.sub(r"^\s*[\*\-]\s*", "", ai).strip() for ai in action_items if ai.strip()] # Remove bullets and trim
                action_items = [ai for ai in action_items if ai] # Filter out empty strings
            if not action_items and action_items_text.lower() != "none" and action_items_text: # Handle cases where "None" is not used but content is there
                action_items = [action_items_text] if action_items_text else []


        # Fallback if primary parsing fails but text exists
        if not summary_match and not decisions_match and not action_items_match and response_text:
            # Attempt to find at least a summary if no sections are clearly delineated
            first_few_lines = "\n".join(response_text.splitlines()[:5]) # Take first 5 lines as potential summary
            if len(first_few_lines) > 20: # Arbitrary length to consider it a summary
                 summary = first_few_lines + " (Note: Full structure parsing failed)"


    except Exception as e:
        print(f"Error parsing LLM response: {e}")
        summary = "Error parsing LLM output. Raw output might be available in logs."
        # Potentially return raw response_text here if needed for debugging on client
        # decisions = [f"Raw response: {response_text}"]

    return {
        "summary": summary,
        "decisions": decisions if decisions else ["None identified." if not summary.startswith("Error parsing") else ""],
        "action_items": action_items if action_items else ["None identified." if not summary.startswith("Error parsing") else ""],
    }


# Updated AI Service using Gemini
def call_ai_service(transcript_text):
    """
    Calls the Google Gemini API to process the transcript text.
    """
    if not GOOGLE_API_KEY or not hasattr(genai, 'GenerativeModel'):
        print("Error: Gemini API key not configured or library not available.")
        return {
            "summary": "AI service is not configured.",
            "decisions": [],
            "action_items": []
        }

    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest') # Or 'gemini-pro' or other suitable model
        
        prompt = f"""
You are an expert meeting assistant tasked with meticulously analyzing transcripts to extract all crucial information.
Here is the transcript of a meeting:
---
{transcript_text}
---
Carefully analyze the entire transcript and provide the following:

1.  **Summary:** A concise summary of the main topics discussed and the overall outcome of the meeting (target 2-4 sentences).

2.  **Key Decisions:** A comprehensive, bulleted list of ALL significant decisions made during the meeting. Be thorough and ensure no decision is missed. If a decision involves a choice between options, state the chosen option clearly.

3.  **Action Items:** A comprehensive, bulleted list of ALL specific action items mentioned. For each action item, include:
    *   The task to be performed.
    *   Who is assigned to the task (if mentioned).
    *   Any deadlines associated with the task (if mentioned).
    Be thorough and ensure no action item is missed.

Format your response clearly with these exact headings on separate lines:
Summary:
[Your summary here]

Key Decisions:
* [Decision 1 - be specific and comprehensive]
* [Decision 2 - be specific and comprehensive]
(Continue for all decisions. If absolutely no decisions were made, write "None" on a new line under this heading.)

Action Items:
* [Action Item 1 - Task: (description), Assigned to: (name/team if specified, otherwise "Not specified"), Deadline: (date/time if specified, otherwise "Not specified")]
* [Action Item 2 - Task: (description), Assigned to: (name/team if specified, otherwise "Not specified"), Deadline: (date/time if specified, otherwise "Not specified")]
(Continue for all action items. If absolutely no action items were identified, write "None" on a new line under this heading.)

Ensure each decision and action item is a separate bullet point. Strive for accuracy and completeness in capturing all key points.
"""
        
        print(f"Sending prompt to Gemini: {prompt[:300]}...") # Log first 300 chars of prompt
        
        # Generation Configuration (optional, for more control)
        generation_config = genai.types.GenerationConfig(
            # temperature=0.7, # Example: Adjust creativity
            # max_output_tokens=1024 # Example: Limit response length
        )

        response = model.generate_content(prompt, generation_config=generation_config)
        
        print(f"Gemini raw response text: {response.text[:300]}...") # Log first 300 chars of response

        # Parsing the response text
        # This part needs to be robust. For now, let's assume a simple structure.
        # A more robust solution might involve asking the LLM to return JSON.
        
        # For now, we'll use a helper function to parse the structured text
        parsed_results = parse_llm_response(response.text)
        return parsed_results

    except Exception as e:
        print(f"Error calling Google Gemini API: {e}")
        # Check for specific API errors if the library provides them
        # e.g. if hasattr(e, 'message'): error_message = e.message
        # else: error_message = str(e)
        return {
            "summary": f"Error communicating with AI service: {str(e)}",
            "decisions": [],
            "action_items": []
        }

ALLOWED_EXTENSIONS = {'txt'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/summarize', methods=['POST'])
def summarize_transcript():
    transcript_text = None

    # Priority 1: JSON payload
    if request.is_json:
        data = request.get_json()
        if not data: # Handle empty JSON body
             return jsonify({"error": "Invalid JSON payload. Expected 'transcript_text'."}), 400
        transcript_text = data.get('transcript_text')

    # Priority 2: Form data (for 'transcript_text' field)
    if not transcript_text and 'transcript_text' in request.form:
        form_text = request.form['transcript_text'].strip()
        if form_text:
            transcript_text = form_text
    
    # Priority 3: File upload
    if not transcript_text and 'transcript_file' in request.files:
        file = request.files['transcript_file']
        if file.filename == '':
            # File part exists but no file selected, this is only an error if no text was provided otherwise
            pass
        elif file and allowed_file(file.filename):
            try:
                transcript_text = file.read().decode('utf-8')
            except Exception as e:
                print(f"Error processing file: {e}")
                return jsonify({"error": f"Error processing file: {e}"}), 500
        elif file: # File exists but not an allowed type
            return jsonify({"error": "Invalid file type. Please upload a .txt file or provide text via 'transcript_text'."}), 400
    
    if not transcript_text:
        return jsonify({"error": "No transcript content provided. Use 'transcript_text' in JSON/form or 'transcript_file' for file upload."}), 400

    try:
        ai_results = call_ai_service(transcript_text)
        return jsonify(ai_results), 200
    except Exception as e:
        print(f"Error calling AI service or processing: {e}")
        # It's good practice to not expose raw exception messages to the client in production
        return jsonify({"error": "An unexpected error occurred during summarization."}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)