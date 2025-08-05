from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import SignUpForm

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # 登録後、自動ログイン
            return redirect('/')  # 遷移先を適宜変更
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})
