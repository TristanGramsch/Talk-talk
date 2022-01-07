# python -m uvicorn main:app --reload
# TODO We must produce a containerazed version that comes with packages.
from fastapi import FastAPI, Request
from config import slack, openApi
from threading import Thread
from random import randint
import requests
import openai

# Set up keys.
openai.api_key = openApi
app = FastAPI()

# More setup
@app.get("/")
async def root():
    return {"message": "Hello World"}
words = []
url = slack
# Object to make the machine work.
def parseText(response):
    response = dict(response)

    choices = response["choices"][0]

    text = choices["text"]
    return text

def learn(word, id):
    prompt = 'The following is a list of words in Spanish for English students to learn\n\nadjectives: deslumbrante (dazzling), nuevo (new), bien (well), simpático (sympathetic), diferente (different), intenso (intense), feliz (happy), imposible (impossible), atractivo (attractive), pobre (poor).\nwork: profesional (professional), cuidar (to take care), incapacitado (incapacitated), pago (payment), conocimiento (knowledge), reclutar (recruit), estudiar (study), empresa (company), vacaciones (vacation), cambio (change), colaborar (collaborate), jefe (boss), carpintero (carpenter), proyecto (project).\n' + word + ':'
    print("Learn prompt:", prompt)

    response = openai.Completion.create(
        engine='davinci',
        prompt=prompt,
        temperature=0.5,
        max_tokens=100,
        top_p=1,
        frequency_penalty=0.25,
        presence_penalty=0.25,
        stop=["\n"]  
    )

    text = parseText(response)
    print('response', text)

    words = text.split(',')
    print("Words:", words)

    answer = words[0].split('(')[0]
    print('Word:', answer)

    data = {'text': answer, "thread_ts": id}
    requests.post(url, json = data)

    globals()[id] = { "word":word, "words":words, "index":0, "score":0 }
    return words


def evaluate(word, id, thread_id):
    thread = globals()[thread_id]
    print('Thread', thread)

    words = thread.get('words')
    print('words', words)

    answer = words[thread.get('index')].split('(')
    print('answer', answer)

    answer = answer[1].replace(')', '')
    print('answer', answer)
    
    answer_word = answer.lower().replace(' ', '').replace('.', '')
    word = word.lower().replace(' ', '').replace('.', '')
    print(answer_word, word)

    response = ''
    if answer_word != word:
        data = {'text':'No, the answer is "' + answer + '"', "thread_ts": id}
        requests.post(url, json = data)

    else:
        good_responses = [ 'Congratulations!', 'Yes, that’s right.', 'Correct!', 'Good Job!', 'Well Done!' ]
        response = good_responses[randint(0, len(good_responses) - 1)] + '\n'


    newIndex = globals()[thread_id]["index"] + 1
    globals()[thread_id]["index"] = newIndex

    nextWord = words[newIndex].split('(')[0]

    data = {'text':response + nextWord, "thread_ts":id}
    requests.post(url, json = data)

    return


def sample_sentence(word):
    prompt = "Teach me a sentence in Spanish with \"negocio\":\n\nEl negocio es una actividad lucrativa que se puede desarrollar en cualquier parte del mundo.\n\n###\n\nTeach me a sentence in Spanish with \"frutas\":\n\nLas frutas son una fuente de vitaminas y minerales que nos ayuda a mantenernos sanos.\n\n###\n\nTeach me a sentence in Spanish with " + word + ":"

    response = openai.Completion.create(
        engine="davinci-instruct-beta",
        prompt=prompt,
        temperature=0.5,
        max_tokens=100,
        top_p=1,
        frequency_penalty=0.25,
        presence_penalty=0.25,
        stop=["###"]
    )    

    text = parseText(response)
    print('response', text)



@app.post('/')
async def slack(request: Request):
    body = await request.json()

    # return body.get('challenge')

    event = body["event"]

    text = event["text"]
    id = event["ts"]
    message = event["type"]
    user = event.get("user")


    # app is mentioned
    if message == 'app_mention':
        text = text.replace('<@U02E7R8BWAD>', '')
        globals()['word'] = text
        Thread(target=learn, args=(text, id)).start()

    # message is from user (filters bot replies).
    elif user:
        thread_ts = event.get("thread_ts")

        # message comes in a thread.
        if thread_ts:
            block = event.get('blocks')[0]
            element = block.get('elements')[0]
            text = element.get('elements')[0].get('text')
            Thread(target=evaluate, args=(text, id, thread_ts)).start()

    return
