FROM node:18-alpine
WORKDIR /app
COPY ./app /app
RUN npm install --silent
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "start"]