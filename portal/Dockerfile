FROM node:18-alpine
WORKDIR /app
COPY ./app /app
RUN npm install --silent
EXPOSE 3000
CMD ["npm","run","dev","--","-H","0.0.0.0"]