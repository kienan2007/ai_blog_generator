from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
from pytubefix import YouTube
import os
import assemblyai as aai
import openai
from django.http import JsonResponse
from .models import BlogPost
from dotenv import load_dotenv
# Create your views here.

load_dotenv()
client = openai.OpenAI(api_key=os.environ.get('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'))
aai.settings.api_key = os.environ.get('6c0197a8fd5543e49aafb76504fa4d6c')

@login_required
def index(request):
    return render(request, 'index.html')

@csrf_exempt
def generate_blog(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            yt_link = data['link']
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({'error': 'invalid data sent'}, status = 400)
    
        #getting yt title
        title = yt_title(yt_link)

        #getting transcript
        transcription = get_transcription(yt_link)
        if not get_transcription:
            return JsonResponse({'error': "Failed to generate blog article"}, status=500)
        
        #generating blog using OpenAI
        blog_content = generate_blog_from_transcription(transcription)
        if not blog_content:
            return JsonResponse({'error': "Failed to get transcript"}, status=500) 
        
        #saving blog article to databases
        new_blog_article = BlogPost.objects.create(
            user = request.user,
            youtube_title = title,
            youtube_link = yt_link, 
            generated_content = blog_content,
        )
        new_blog_article.save()

        #returning blog article as a response
        return JsonResponse({'content': blog_content})
    else:
        return JsonResponse({'error': 'invalid request method'}, status = 405)
def yt_title(link):
        yt = YouTube(link)
        title = yt.title
        return title


def download_audio(link):
    yt = YouTube(link)
    video = yt.streams.filter(only_audio=True).first()
    out_file = video.download(output_path=settings.MEDIA_ROOT)
    base, ext = os.path.splitext(out_file)
    new_file = base + '.mp3'
    os.rename(out_file, new_file)
    return new_file

def get_transcription(link):
    audio_file = download_audio(link)
    aai.settings.api_key = "6c0197a8fd5543e49aafb76504fa4d6c"
    config = aai.TranscriptionConfig(speech_models=[aai.SpeechModel.universal])

    transcriber = aai.Transcriber(config = config)
    transcript = transcriber.transcribe(audio_file)

    return transcript.text 

def generate_blog_from_transcription(transcription):
    client = openai.OpenAI(api_key="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")

    prompt = f"Base on the following transcript from a Youtube video, write a comprehensive blog article, write it based on the transcript, make it look like a proper blog article:\n\n{transcription}\n\nArticle:"

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000
    )

    generated_content = response.choices[0].message.content.strip()
    return generated_content

def blog_list(request):
    blog_articles = BlogPost.objects.filter(user = request.user)
    return render(request, 'all-blogs.html', {'blog_articles': blog_articles})

def blog_details(request, pk):  
    blog_article_detail = BlogPost.objects.get(id=pk)
    if request.user == blog_article_detail.user:
        return render(request, 'blog-details.html', {'blog_article_detail': blog_article_detail})
    else:
            return redirect('/')

def user_login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username = username, password = password)
        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            error_message = 'Invalid username or password'
            return render(request, 'signup.html', {"error_message" : error_message})
        
    return render(request, 'login.html')

def user_signup(request):
    if request.method == "POST":
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        repeatPassword = request.POST['repeatPassword']

        if password == repeatPassword:
            try:
                user = User.objects.create_user(username,email,password)
                user.save()
                login(request, user)
                return redirect('/')
            except:
                error_message = 'Error creating account'
                return render(request, 'signup.html', {"error_message" : error_message})
        else:
            error_message = 'Password does not match'
            return render(request, 'signup.html', {'error_message' : error_message})
    
    return render(request, 'signup.html')

def user_logout(request):
    logout(request)
    return redirect('/')