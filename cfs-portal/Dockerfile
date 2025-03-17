FROM node:14

WORKDIR /usr/app

COPY package*.json ./

RUN npm install

COPY . /usr/app

CMD ["npm", "start"]
