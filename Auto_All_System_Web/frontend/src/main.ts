import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './styles/index.scss'
import UiPlugin from './plugins/ui'

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(UiPlugin)

app.mount('#app')
