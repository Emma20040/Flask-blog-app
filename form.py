from flask import Flask
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, EmailField, PasswordField
from wtforms.validators import InputRequired, Length, EqualTo
from flask_ckeditor import CKEditor
from flask_ckeditor import CKEditorField


class PostForm(FlaskForm):
    title = StringField('Title', [InputRequired(message='Please give a title to your post')])
    subtitle = StringField('Subtitle')
    image =StringField('Image_url')
    content =CKEditorField('Blog Content')
    # author =StringField('Author', [InputRequired(message='please include the author of this post')])
    submit =SubmitField('submit')

class LoginForm(FlaskForm):
    name = StringField('Name', [InputRequired(message='please username is required for authentication')])
    email = EmailField('Email', [InputRequired(message='please enter a valid email address')])
    password = PasswordField('Password', [InputRequired(message='please create a password'), 
                                          Length( max =300, min=8)])
    confirm_password = PasswordField('Confirm Password', 
                                     [InputRequired(message='your two passwords must match'), EqualTo('password')])
    # submit button for sign up
    submit_up = SubmitField('Sign Up')
    # submit button for sign in
    submit_in = SubmitField('Sign in')