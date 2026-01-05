import os
import logging
import random
import time

# Configure logging
logger = logging.getLogger(__name__)

class ASRHandler:
    def __init__(self):
        self.groq_key = os.getenv('ASR_GROQ_API_KEY')
        self.openai_key = os.getenv('ASR_OPENAI_API_KEY')
        self.gemini_key = os.getenv('ASR_GEMINI_API_KEY') or os.getenv('GEMINI_API_KEY')
        self.default_provider = os.getenv('ASR_DEFAULT_PROVIDER', 'groq').lower()
        
        self.groq_client = None
        self.openai_client = None
        
        if self.groq_key:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=self.groq_key)
            except ImportError:
                logger.error("Groq library not installed")
            except Exception as e:
                logger.error(f"Failed to initialize Groq client: {e}")
        
        if self.openai_key:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=self.openai_key)
            except ImportError:
                logger.error("OpenAI library not installed")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                
        if self.gemini_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_key)
            except Exception as e:
                logger.error(f"Failed to configure Gemini: {e}")

    def transcribe_groq(self, file_path):
        if not self.groq_client:
            raise Exception("Groq client not initialized (Check ASR_GROQ_API_KEY)")
        
        with open(file_path, "rb") as file:
            # Groq Whisper implementation
            transcription = self.groq_client.audio.transcriptions.create(
                file=file,
                model="whisper-large-v3",
                temperature=0,
                response_format="text"
            )
        return str(transcription)

    def transcribe_openai(self, file_path):
        if not self.openai_client:
            raise Exception("OpenAI client not initialized (Check ASR_OPENAI_API_KEY)")
            
        with open(file_path, "rb") as audio_file:
            transcription = self.openai_client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
        return transcription.text

    def transcribe_gemini(self, file_path):
        if not self.gemini_key:
            raise Exception("Gemini key not configured")
            
        import google.generativeai as genai
        # Gemini 1.5 Flash is efficient for audio
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Upload the file
        logger.info(f"Uploading file to Gemini: {file_path}")
        audio_file = genai.upload_file(path=file_path)
        
        # Wait for processing if necessary (usually fast)
        while audio_file.state.name == "PROCESSING":
            time.sleep(1)
            audio_file = genai.get_file(audio_file.name)

        if audio_file.state.name == "FAILED":
            raise Exception("Gemini file processing failed")

        response = model.generate_content(
            ["Please transcribe this audio file exactly as it is spoken. Do not add any other text.", audio_file]
        )
        
        return response.text

    def transcribe(self, file_path):
        providers = [self.default_provider]
        others = ['groq', 'openai', 'gemini']
        if self.default_provider in others:
            others.remove(self.default_provider)
        random.shuffle(others)
        providers.extend(others)
        
        last_error = None
        
        for provider in providers:
            try:
                logger.info(f"Attempting ASR with {provider}")
                if provider == 'groq':
                    return self.transcribe_groq(file_path)
                elif provider == 'openai':
                    return self.transcribe_openai(file_path)
                elif provider == 'gemini':
                    return self.transcribe_gemini(file_path)
            except Exception as e:
                logger.warning(f"ASR failed with {provider}: {e}")
                last_error = e
                continue
        
        raise Exception(f"All ASR providers failed. Last error: {last_error}")
