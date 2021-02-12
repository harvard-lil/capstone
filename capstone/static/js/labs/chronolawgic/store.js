import Vue from 'vue'
import Vuex from 'vuex'
import axios from "axios";


// eslint-disable-next-line
const import_urls = urls; // defined in timeline.html

Vue.use(Vuex)
const store = new Vuex.Store({
    state: {
        urls: { // Doing this the long way to make it a little easier to see what's going on.
            chronolawgic_api_create: import_urls.chronolawgic_api_create,
            chronolawgic_api_retrieve: import_urls.chronolawgic_api_retrieve,
            chronolawgic_api_update: import_urls.chronolawgic_api_update,
            chronolawgic_api_delete: import_urls.chronolawgic_api_delete,
            static: import_urls.static
        },
        available_timelines: [
            //TODO: store a list of timeline titles/ids available on the server
        ],
        id: 1,
        title: "Timeline Title",
        CreatedBy: "Editable Text", // (user accts are for auth/logging purposes)
        categories: {
            Case: {id: "1", color: "#FF9911"},
            Legislation: {id: "2", color: "#99FF11"},
            ExecutiveOrder: {id: "3", color: "#FF9988"},
            Anarchism: {id: "4", color: "#11FF99"},
            Police: {id: "5", color: "#8899FF"},
            Fascism: {id: "6", color: "#1199FF"},
        },
        events: [ {
                name: "Event 1",
                url: "https://cite.case.law/ill/1/176/",
                description: "Between some time and some other time, this thing happened.",
                start_year: 1880,
                start_month: 1,
                start_day: 15,
                end_year: 1889,
                categories: [2, 4],
                end_month: 1,
                end_day: 15,
        }],
        cases: [
            {
                name: "Case 1",
                subhead: "Case 1",
                description: "Though the Court upheld a conviction for membership in a group that advocated the overthrow of the state, Justice Brandeis explained, in a separate opinion, that under the \"clear and present danger test\" the strong presumption must be in favor of \"more speech, not enforced silence.\" That view, which ultimately prevailed, laid the groundwork for modern First Amendment law.",
                decision_date: "",
                categories: [1, 3],
                url: "https://cite.case.law/ill/1/176/",
                jurisdiction: "Ill.",
                reporter:  "Ill.",
                isCap: true,
                year: 1885,
                month: 12,
                day: 30,
            },
        ]
    },
    mutations: {
        writeTimeline(state) {
            //TODO: Do any data transformations necessary
            //TODO: Check credentials
            //TODO: Send updated timeline to server
            state.placeholder = 9;
        },
        createTimeline(state) {
            //TODO: Check credentials
            //TODO: Get new timeline ID from server
            state.placeholder = 9;
        },
        deleteTimeline(state) {
            //TODO: Do any data transformations necessary
            state.placeholder = 9;
        },
        setTimeline(state) {
            //TODO: Do any data transformations necessary
            // state.timeline = state.timeline;
            console.log("setTimeline", state.timeline)
        }
    },
    getters: {
        readTimeline(state) {
            state.placeholder++
        },
        getEvents(state) {
            return state.timeline.events;
        },
    },
    actions: {
        deserialize: (json) => {
            this.state.id = json.id
            this.state.title = json.title
            this.state.CreatedBy = json.CreatedBy
            this.state.categories = json.categories
            this.state.events = json.events
            this.state.cases = json.cases
        },
        serialize: () => {
            return {
                id: this.state.id,
                title: this.state.title,
                CreatedBy: this.state.CreatedBy,
                categories: this.state.categories,
                events: this.state.events,
                cases: this.state.cases,
            }
        },
        getTimeLine: function ({commit}) {
            //TODO make this work with vue router so it gets the new timeine as the route changes
            axios
                .get(this.state.urls.chronolawgic_api_retrieve)
                .then(response => response.data)
                .then(timeline => {
                    console.log(timeline);
                    commit('setTimeline', timeline)
                })
        },
    },
})
export default store;