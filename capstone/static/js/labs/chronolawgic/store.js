import Vue from 'vue'
import Vuex from 'vuex'
import ClientConfig from './chronolawgic-client-config.json'
import axios from "axios";

Vue.use(Vuex)
const store = new Vuex.Store({
    state: {
        placeholder: 'placeholder',
        authentication: {
            "name": "test user", // what is their name?
            "token": false, // What is their server authentication token?
            "admin_users": false, // Can this user administer users?
            "can_create": false, // Can this user create new timelines?
            "timelines": [] // What timelines can this user edit?
        },
        available_timelines: [
            //TODO: store a list of timeline titles/ids available on the server
        ],
        timeline: {
            //TODO: timeline structure

            id: 1,
            title: "Timeline Title",
            created_by: "Editable Text", // (user accts are for auth/logging purposes)
            categories: {
                Case: {id: "1", color: "#FF9911"},
                Legislation: {id: "2", color: "#99FF11"},
                ExecutiveOrder: {id: "3", color: "#FF9988"},
                Anarchism: {id: "4", color: "#11FF99"},
                Police: {id: "5", color: "#8899FF"},
                Fascism: {id: "6", color: "#1199FF"},
            },
            events: {
                0: {
                    title: "Case 1",
                    categories: [1, 3],
                    cap_link: "https://cite.case.law/ill/1/176/",
                    link: false,
                    description: "Though the Court upheld a conviction for membership in a group that advocated the overthrow of the state, Justice Brandeis explained, in a separate opinion, that under the \"clear and present danger test\" the strong presumption must be in favor of \"more speech, not enforced silence.\" That view, which ultimately prevailed, laid the groundwork for modern First Amendment law.",
                    start_year: 1880,
                    thumb: 123,
                },
                1: {
                    title: "Case 2",
                    categories: [1, 2],
                    cap_link: "https://cite.case.law/ill/1/176/",
                    link: false,
                    description: "Our first Supreme Court landmark. Though upholding the defendant's conviction for distributing his call to overthrow the government, the Court held, for the first time, that the Fourteenth Amendment \"incorporates\" the free speech clause of the First Amendment and is, therefore, applicable to the states.",
                    start_year: 1881,
                    thumb: 123,
                    // What else do we need? Disposition? Collapsed/Visible? Hidden? Draft? Author?
                },
                2: {
                    title: "Case 3",
                    categories: [1, 2],
                    cap_link: "https://cite.case.law/ill/1/176/",
                    link: false,
                    description: "Our first Supreme Court landmark. Though upholding the defendant's conviction for distributing his call to overthrow the government, the Court held, for the first time, that the Fourteenth Amendment \"incorporates\" the free speech clause of the First Amendment and is, therefore, applicable to the states.",
                    start_year: 1880,
                    thumb: 123,
                    // What else do we need? Disposition? Collapsed/Visible? Hidden? Draft? Author?
                }
            },
            years: {1880: [0, 2], 1881: [1]},
            app_meta: { // DOESN'T GET EXPORTED — implementation specific
                acl: [],
                created_by: 1,
                is_draft: true,
                is_hidden: false,
            },
        },
        updated_timeline: {
            //TODO: updated timeline structure to store edits
        }
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
        authenticate(credentials = false) {
            console.log("authenticating with :")
            console.log(credentials)
            return false
        },
        getTimeLine: function ({commit}) {
            //TODO make this work with vue router so it gets the new timeine as the route changes
            axios
                .get(ClientConfig.server_url)
                .then(response => response.data)
                .then(timeline => {
                    console.log(timeline);
                    commit('setTimeline', timeline)
                })
        },
    },
})
export default store;