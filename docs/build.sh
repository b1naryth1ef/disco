#!/bin/bash
gitbook build
rsync -avzP _book/* meph:/var/www/disco/
