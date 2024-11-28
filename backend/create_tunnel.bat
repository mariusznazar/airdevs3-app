@echo off
echo Pamietaj: dla uzytkownika 51983 haslo to rowniez 51983
echo Tworzenie tunelu SSH z debugowaniem...
ssh -v -N -p 5022 -R "0.0.0.0:51983:127.0.0.1:8000" 51983@azyl.ag3nts.org 