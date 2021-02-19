import Vue from 'vue'
import Vuex from 'vuex'
import axios from "axios";
import {router} from "./main.js"

axios.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios.defaults.xsrfCookieName = "csrftoken";

// eslint-disable-next-line
const importUrls = urls; // defined in timeline.html
// eslint-disable-next-line
const importChoices = choices; // defined in timeline.html

Vue.use(Vuex);
const store = new Vuex.Store({
    state: {
        choices: importChoices,
        requestStatus: 'complete',
        errorMessage: [],
        statusMessage: [],
        urls: { // Doing this the long way to make it a little easier to see what's going on.
            chronolawgic_api_create: importUrls.chronolawgic_api_create,
            chronolawgic_api_retrieve: importUrls.chronolawgic_api_retrieve,
            chronolawgic_api_update: importUrls.chronolawgic_api_update,
            chronolawgic_api_delete: importUrls.chronolawgic_api_delete,
            static: importUrls.static,
            api_root: importUrls.api_root,
        },
        availableTimelines: [],
        id: 1,
        title: "Timeline Title",
        createdBy: "Editable Text", // (user accts are for auth/logging purposes)
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
        ],
        templateEvent: {
            url: "",
            name: "",
            short_description: "",
            long_description: "",
            jurisdiction: "",
            reporter: "",
            start_date: "",
            end_date: "",
            categories: [],
        }
    },
    mutations: {
        writeTimeline(state) {
            //TODO: Do any data transformations necessary
            //TODO: Check credentials
            //TODO: Send updated timeline to server
            state.placeholder = 9;
        },
        deleteTimeline(timeline_id) {
            //todo
            console.log("deleteTimeLine" + timeline_id)
        },
        setAvailableTimelines(state, json) {
            state.availableTimelines = json
        },
        setTimeline(state, json) {

            state.title = json.title;
            state.CreatedBy = json.CreatedBy;
            state.categories = json.categories;
            state.events = json.events;
            state.cases = json.cases
        },
        setTimelineId(state, timeline_id) {
            state.id = timeline_id
        },
        setRequestStatus(state, status) {
            state.requestStatus = status
        },
        setStatusMessage(state, call, status, timelineId=null) {
            state.statusMessage.push({
                "call": call,
                "timelineId": timelineId,
                "status": status
            })
        },
        /*
        addEvent(state, name, url, description, start_year, end_year, start_day, end_day, categories, end_month) {
            state.events.push({
                name: name,
                url: url,
                description: description,
                start_year: start_year,
                start_month: end_year,
                start_day: start_day,
                end_year: end_day,
                categories: [],
                end_month: end_month,
                end_day: end_day,
            })
        },
        updateEvent(state, index, name, url, description, start_year, end_year, start_day, end_day, categories, end_month) {
            state.events[index] = {
                name: name,
                url: url,
                description: description,
                start_year: start_year,
                start_month: end_year,
                start_day: start_day,
                end_year: end_day,
                categories: [],
                end_month: end_month,
                end_day: end_day,
            }
        },
        deleteEvent(state, index) {
            state.events.remove(index);
        },
        addCase(state, name, subhead, url, description, decision_date, jurisdiction, reporter, isCap, categories, year, month, day) {
            //todo
        },
        updateCase(state, index, name, subhead, url, description, decision_date, jurisdiction, reporter, isCap, categories, year, month, day) {
            //todo
        },
        deleteCase(state, index) {
            //todo
        },
        */
    },
    getters: {
        events: state => state.events,
        availableTimelines: state => state.availableTimelines,
        id: state => state.id,
        requestStatus: state => state.requestStatus,
        cases: state => state.cases,
        templateEvent: state => state.templateEvent,
    },
    actions: {
        serialize: ({state}) => {
            return {
                id: state.id,
                title: state.title,
                CreatedBy: state.CreatedBy,
                categories: state.categories,
                events: state.events,
                cases: state.cases,
            }
        },
        requestCreateTimeline: function ({commit}) {
            commit('setRequestStatus', 'pending');
            axios
                .post(this.state.urls.chronolawgic_api_create)
                .then(response => response.data)
                .then(new_tl => {
                    if (new_tl.status === "ok") {
                        this.dispatch('requestTimelineList');
                        router.push({ name: 'timeline', params: { timeline: new_tl.id } })
                    }
                }).then(
                    () => { commit('setRequestStatus', 'complete') }
                ).catch(error => {
                    commit('setRequestStatus', 'error')
                    commit('setStatusMessage', 'requestCreateTimeline', error, null)
                })
        },
        requestDeleteTimeline: function ({commit}, timelineId) {
            commit('setRequestStatus', 'pending');
            axios
                .delete(this.state.urls.chronolawgic_api_delete + timelineId)
                .then(response => response.data)
                .then(timeline => {
                    if (timeline.status === "ok") {
                        this.dispatch('requestTimelineList');
                    }
                }).then(
                    () => { commit('setRequestStatus', 'complete') }
                ).catch(error => {
                    commit('setRequestStatus', 'error')
                    commit('setStatusMessage', 'requestDeleteTimeline', error, timelineId)
                })
        },
        requestUpdateTimeline: function ({commit}, timelineId) {
            commit('setRequestStatus', 'pending');
            axios
                .delete(this.state.urls.chronolawgic_api_update + timelineId)
                .then(response => response.data)
                .then(timeline => {
                    if (timeline.status === "ok") {
                        this.requestTimelineList();
                        commit('setDeletedStatus', timeline['timeline'])
                    }
                }).then(
                    () => { commit('setRequestStatus', 'complete') }
                ).catch(error => {
                    commit('setRequestStatus', 'error')
                    commit('setStatusMessage', 'requestUpdateTimeline', error, timelineId)
                })
        },
        requestTimeline: function ({commit}, timelineId) {
            commit('setRequestStatus', 'pending');
            axios
                .get(this.state.urls.chronolawgic_api_retrieve + timelineId)
                .then(response => response.data)
                .then(timeline => {
                    if (timeline.status === "ok") {
                        commit('setTimeline', timeline['timeline'])
                    }
                }).then(
                    () => { commit('setRequestStatus', 'complete') }
                ).catch(error => {
                    commit('setRequestStatus', 'error')
                    commit('setStatusMessage', 'requestDeleteTimeline', error, timelineId)
                })
        },
        requestTimelineList: function ({commit}) {
            commit('setRequestStatus', 'pending');
            axios
                .get(this.state.urls.chronolawgic_api_retrieve)
                .then(response => response.data)
                .then(availableTimelines => {
                    if (availableTimelines.status === "ok") {
                        commit('setAvailableTimelines', availableTimelines['timelines'])
                    }
                }).then(
                    () => { commit('setRequestStatus', 'complete') }
                ).catch(error => {
                    commit('setRequestStatus', 'error')
                    commit('setStatusMessage', 'requestDeleteTimeline', error, null)
                })
        }
    }
});
export default store;