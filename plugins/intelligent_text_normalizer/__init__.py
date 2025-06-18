import pandas as pd
from pathlib import Path
import logging

# Attempt to import transformers pipeline
try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    pipeline = None # Make sure pipeline is defined for type hinting if not available

from typing import Optional # For current_user type hint

# Audit Logger
from app.core.audit_logger import log_audit_event, ACTION_PLUGIN_LLM_NORMALIZER_USED

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# LLM Model Configuration
MODEL_NAME = "Gensyn/Qwen2.5-0.5B-Instruct"
# Using a smaller model like "distilgpt2" for quicker testing if Qwen2.5 is too large or slow for sandbox.
# MODEL_NAME = "distilgpt2" # Alternative for faster testing if needed.
llm_pipeline = None
MODEL_PATH_CONFIGURED = False

if TRANSFORMERS_AVAILABLE:
    logger.info(f"Attempting to initialize LLM model: {MODEL_NAME}")
    try:
        # Initialize the LLM pipeline
        # Using device=-1 for CPU to ensure compatibility in environments without GPU
        # trust_remote_code=True might be needed for some models.
        llm_pipeline = pipeline("text-generation", model=MODEL_NAME, device=-1) # trust_remote_code=True if required
        MODEL_PATH_CONFIGURED = True
        logger.info(f"Successfully initialized LLM model '{MODEL_NAME}' for IntelligentTextNormalizer.")
    except Exception as e:
        llm_pipeline = None
        MODEL_PATH_CONFIGURED = False
        logger.error(
            f"Failed to initialize LLM model '{MODEL_NAME}' for IntelligentTextNormalizer. "
            f"Plugin will operate in passthrough mode or skip processing. Error: {e}",
            exc_info=True
        )
else:
    logger.warning(
        "The 'transformers' library is not installed. "
        "IntelligentTextNormalizer will not perform LLM-based normalization. "
        "Please install 'transformers' and 'torch' to enable this feature."
    )
    MODEL_PATH_CONFIGURED = False


def format_prompt(text_to_normalize: str, normalization_rules: str) -> str:
    """
    Formats a prompt for the LLM model, instructing it to return only the normalized text.
    """
    # Ensure the prompt clearly instructs the LLM.
    # The key is to guide the model to output *only* what's needed.
    # Adding a clear delimiter like "Normalized text:" helps in parsing.
    return (
        f"Please normalize the following text based on these rules: '{normalization_rules}'.\n"
        f"Original text: '''{text_to_normalize}'''\n"
        f"Return only the normalized text, with no additional explanation, labels, or markdown formatting.\n"
        f"Normalized text:" # This acts as a cue for the model and a split point.
    )

def parse_llm_output(full_output: str, prompt: str) -> str:
    """
    Extracts the newly generated (normalized) text from the LLM's full output.
    This function assumes the prompt structure from format_prompt, particularly the "Normalized text:" part.
    """
    # Option 1: Split by the end of the prompt cue.
    # This is often more reliable than just taking what's after the prompt if the model is verbose.
    cue = "Normalized text:"
    if cue in full_output:
        # Find the last occurrence of the cue in case the model echoes it.
        parts = full_output.split(cue)
        if len(parts) > 1:
            normalized_text = parts[-1].strip()
            # Further clean-up: remove potential model self-reflections or EOS tokens if they appear.
            # This might need to be adapted based on observed model behavior.
            # For example, some models might add "<|endoftext|>" or similar.
            # common_eos_tokens = ["<|endoftext|>", "<|im_end|>", "</s>"]
            # for token in common_eos_tokens:
            #    if normalized_text.endswith(token):
            #        normalized_text = normalized_text[:-len(token)].strip()
            return normalized_text

    # Fallback Option 2: If the cue is not found in the output (e.g., model didn't follow instructions)
    # try to remove the prompt text from the beginning of the output.
    # This is less robust if the model slightly modifies the prompt in its output.
    if full_output.startswith(prompt):
        return full_output[len(prompt):].strip()

    # Fallback Option 3: Return the output as is, with a warning, if parsing fails.
    logger.warning(f"Could not reliably parse LLM output. Using raw output. Full output: '{full_output}'")
    return full_output.strip()


def process(df: pd.DataFrame, current_user: Optional[dict] = None, **params) -> pd.DataFrame:
    """
    Processes the DataFrame to normalize text in specified columns using LLM.
    Includes current_user for audit logging.
    """
    user_id = current_user.get('id') if current_user else None
    username = current_user.get('username') if current_user else "System"

    logger.info(f"IntelligentTextNormalizer process started by user '{username}'. Model Configured: {MODEL_PATH_CONFIGURED}")

    columns = params.get("columns")
    normalization_rules = params.get("normalization_rules")
    max_new_tokens_param = params.get("max_new_tokens", 50) # Default if not provided

    if not columns:
        raise ValueError("The 'columns' parameter must be provided for IntelligentTextNormalizer.")

    if not normalization_rules:
        logger.warning("The 'normalization_rules' parameter was not provided. Skipping normalization.")
        return df

    result_df = df.copy()

    if not MODEL_PATH_CONFIGURED or llm_pipeline is None:
        logger.warning(
            "LLM model for IntelligentTextNormalizer is not available or not configured. "
            "Skipping actual LLM processing. DataFrame will be returned as is."
        )
        # Log what would have been done (as in previous version)
        for col_name in columns:
            if col_name not in result_df.columns:
                logger.warning(f"Column '{col_name}' not found in DataFrame. Skipping.")
                continue
            logger.info(f"Would process column '{col_name}' with rules: '{normalization_rules}'. (LLM not active)")
            for index, row in result_df.head().iterrows(): # Log for a few head rows
                 text_to_normalize = str(row[col_name])
                 logger.info(f"  Row {index}, Column '{col_name}': Would normalize text: '{text_to_normalize}'")
        return result_df

    logger.info(f"User '{username}' processing columns {columns} with LLM using rules: '{normalization_rules}'")

    # Log the audit event for using this plugin
    # This is logged once per plugin execution, not per item, to avoid excessive logs.
    log_audit_event(
        action_type=ACTION_PLUGIN_LLM_NORMALIZER_USED,
        outcome="SUCCESS", # Assuming successful trigger, individual errors logged below
        user_id=user_id,
        username=username,
        details={
            "columns_processed": columns,
            "normalization_rules_applied": normalization_rules,
            "model_name": MODEL_NAME
        }
    )

    for col_name in columns:
        if col_name not in result_df.columns:
            logger.warning(f"Column '{col_name}' not found in DataFrame. Skipping this column.")
            continue

        logger.info(f"Normalizing text in column: '{col_name}'")
        processed_count = 0
        failed_count = 0
        for index, row in result_df.iterrows():
            text_to_normalize = str(row[col_name])

            if pd.isna(text_to_normalize) or not text_to_normalize.strip():
                # logger.debug(f"Skipping empty or NaN value at row {index}, column '{col_name}'")
                continue

            try:
                prompt = format_prompt(text_to_normalize, normalization_rules)

                # LLM call parameters
                # max_length can be absolute, max_new_tokens relative to prompt.
                # Adjust max_new_tokens based on expected length of normalized text.
                # For text-generation, the output often includes the prompt.
                llm_output = llm_pipeline(
                    prompt,
                    max_new_tokens=len(text_to_normalize) + max_new_tokens_param, # Allow space for new tokens
                    temperature=0.7, # Adjust for creativity vs. determinism
                    top_p=0.9,       # Nucleus sampling
                    num_return_sequences=1, # We want one best answer
                    # Other params like do_sample=True might be needed depending on model/desired output
                )

                # The output is a list of dictionaries, e.g., [{'generated_text': '...'}]
                if llm_output and isinstance(llm_output, list) and 'generated_text' in llm_output[0]:
                    full_generated_text = llm_output[0]['generated_text']
                    normalized_text = parse_llm_output(full_generated_text, prompt)

                    if text_to_normalize != normalized_text: # Log if actual change happened
                        logger.debug(f"Row {index}, Col '{col_name}': Original: '{text_to_normalize}' -> Normalized: '{normalized_text}'")
                    result_df.at[index, col_name] = normalized_text
                    processed_count +=1
                else:
                    logger.warning(f"LLM output format unexpected for row {index}, col '{col_name}'. Output: {llm_output}")
                    failed_count += 1
                    # Optionally, keep original text: result_df.at[index, col_name] = text_to_normalize

            except Exception as e:
                logger.error(
                    f"Error during LLM inference for row {index}, column '{col_name}'. "
                    f"Text: '{text_to_normalize}'. Error: {e}",
                    exc_info=True # Set to False in production if too verbose
                )
                failed_count += 1
                # Keep original text in case of error
                # result_df.at[index, col_name] = text_to_normalize
        logger.info(f"Finished processing column '{col_name}'. Processed items: {processed_count}, Failed items: {failed_count}")

    logger.info("IntelligentTextNormalizer process finished.")
    return result_df


if __name__ == '__main__':
    # Example Usage (for testing purposes within this file)
    # Ensure transformers and a model like 'distilgpt2' or the specified Qwen model is installed/downloadable.

    logger.info("--- Running Example Usage for IntelligentTextNormalizer ---")

    if not MODEL_PATH_CONFIGURED or llm_pipeline is None:
        logger.error("LLM Pipeline not available. Cannot run full example. Please check model loading and dependencies.")
    else:
        logger.info(f"LLM Pipeline '{MODEL_NAME}' is loaded. Proceeding with example.")
        data = {
            'id': [1, 2, 3, 4, 5, 6],
            'description': [
                "Ths is a product with sme typos and INCORRECT case.",
                "another item desc for normalization please fix it",
                "  leading and trailing spaces test   ",
                "pls remove abbrevs like pls and convert to full words",
                "UPPERCASE TEXT THAT NEEDS TO BE lower cased or sentence cased.",
                "Check this item for any grammer mistakes and speling errors."
            ],
            'notes': [
                "Item is new, box opend for checkng.",
                "minor scratches on scond hand unit.",
                None, # Test NaN handling
                "contact asap", # Test abbreviation
                "VERY URGENT NOTE",
                "" # Test empty string handling
            ]
        }
        sample_df = pd.DataFrame(data)

        params_config = {
            "columns": ["description", "notes"],
            "normalization_rules": "Fix spelling mistakes, correct grammar, ensure consistent sentence case, expand common abbreviations (e.g., 'pls' to 'please', 'asap' to 'as soon as possible').",
            "max_new_tokens": 60 # Give enough room for expansion
        }

        logger.info(f"Original DataFrame:\n{sample_df}")

        processed_df = process(sample_df.copy(), **params_config)

        logger.info(f"Processed DataFrame by {MODEL_NAME}:\n{processed_df}")

        # Example of a more specific rule set for a column
        params_specific_rules = {
            "columns": ["notes"],
            "normalization_rules": "Convert to lowercase. Expand 'asap' to 'as soon as possible'. Remove extra spaces.",
            "max_new_tokens": 40
        }
        logger.info(f"Original Notes Column:\n{sample_df[['notes']]}")
        processed_df_specific = process(sample_df.copy(), **params_specific_rules)
        logger.info(f"Processed Notes Column by {MODEL_NAME} (specific rules):\n{processed_df_specific[['notes']]}")

    logger.info("--- IntelligentTextNormalizer Example Usage Finished ---")
