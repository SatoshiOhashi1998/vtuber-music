from django import forms
from .models import Playlist, PlaylistVideo


class PlaylistForm(forms.ModelForm):
    class Meta:
        model = Playlist
        fields = ['name']


class PlaylistVideoOrderForm(forms.ModelForm):
    class Meta:
        model = PlaylistVideo
        fields = ['order']
