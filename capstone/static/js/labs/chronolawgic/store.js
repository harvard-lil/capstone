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
// eslint-disable-next-line
const importUser = user; // defined in timeline.html

Vue.use(Vuex);
const store = new Vuex.Store({
    state: {
        user: importUser,
        choices: importChoices,
        requestStatus: 'nominal', // can be nominal, success, error, or pending. Prone to race conditions, so use only for user feedback until its improved
        notificationMessage: null,
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
        title: "",
        createdBy: -1, // (user accts are for auth/logging purposes)
        isAuthor: false,
        categories: {}, // Removed from MVP
        events: [],
        cases: [],
        templateEvent: {
            url: "",
            name: "",
            short_description: "",
            long_description: "",
            start_date: "",
            end_date: "",
            categories: [],
        },
        templateCase: {
            url: "",
            name: "",
            citation: "",
            short_description: "",
            long_description: "",
            jurisdiction: "",
            reporter: "",
            decision_date: "",
            categories: [],
        }
    },
    mutations: {
        writeTimeline(state) {
            //TODO
            state.placeholder = 9;
        },
        deleteTimeline() {
            //todo
        },
        setAvailableTimelines(state, json) {
            state.availableTimelines = json
        },
        setTimeline(state, json) {
            state.title = json.title;
            state.categories = json.categories;
            state.events = json.events;
            state.cases = json.cases
        },
        setTimelineId(state, timeline_id) {
            state.id = timeline_id
        },
        setCreatedBy(state, createdBy) {
            state.createdBy = createdBy;
        },
        setAuthor(state, isAuthor) {
            state.isAuthor = isAuthor;
        },
        setRequestStatus(state, status) {
            state.requestStatus = status;
        },
        setRequestStatusTerminal(state, status) {
            state.requestStatus = status;
            setTimeout(function () {
                state.requestStatus = "nominal";
            }, 5000);
        },
        setNotificationMessage(state, message) {
            //TODO Someday— make this a queue and let the notifications stack
            state.notificationMessage = message;
            setTimeout(function () {
                state.notificationMessage = null;
            }, 5000);
        },
        addEvent(state, event) {
            state.events.push(event)
        },
        addCase(state, caselaw) {
            // assign id to caselaw
            let index = -1
            state.cases.forEach((c)=>{
                if (c.id >= index) { index = c.id + 1 }
            });
            caselaw.id = index;
            state.cases.push(caselaw)
            this.dispatch('requestUpdateTimeline')
        },
        updateEvent(state, index, event) {
            state.events[index] = event
        },
        updateCase(state, caselaw) {
            for (let i = 0; i < state.cases.length; i++) {
                if (state.cases[i].id === caselaw.id) {
                    state.cases[i] = caselaw;
                    this.dispatch('requestUpdateTimeline')
                    break;
                }
            }
        },
        deleteEvent(state, index) {
            state.events.remove(index);
        },
        deleteCase(state, id) {
            let caselaw_index = -1;
            for (let i=0; i<state.cases.length; i++) {
                if (state.cases[i].id === id) {
                    caselaw_index = i;
                    break;
                }
            }
            state.cases.splice(caselaw_index, 1);
            this.dispatch('requestUpdateTimeline');
        }
    },
    getters: {
        cases: state => state.cases,
        choices: state => state.choices,
        availableTimelines: state => state.availableTimelines,
        id: state => state.id,
        requestStatus: state => state.requestStatus,
        notificationMessage: state => state.notificationMessage,
        templateEvent: state => state.templateEvent,
        firstYear: (state) => {
            const first_event_year = state.events.reduce((min, e) =>
                new Date(e.start_date).getFullYear() < min ? new Date(e.start_date).getFullYear() : min, new Date(state.events[0].start_date).getFullYear());
            const first_case_year = state.cases.reduce((min, c) => new Date(c.decision_date).getFullYear() < min ? new Date(c.decision_date).getFullYear() : min, new Date(state.cases[0].decision_date).getFullYear());
            return first_case_year < first_event_year ? first_case_year : first_event_year;
        },
        lastYear: (state) => {
            const last_event_year = state.events.reduce((max, e) =>
                new Date(e.end_date).getFullYear() > max ? new Date(e.end_date).getFullYear() : max, new Date(state.events[0].end_date).getFullYear());
            const last_case_year = state.cases.reduce((max, e) =>
                new Date(e.decision_date).getFullYear() > max ? new Date(e.decision_date).getFullYear() : max, new Date(state.cases[0].decision_date).getFullYear());
            return last_case_year > last_event_year ? last_case_year : last_event_year;
        },
        events: (state) => {
            return state.events.sort((a, b) => (a.start_date > b.start_date) ? 1 : -1)
        },
        // eventsByYear: (state) => (year) => {
        //     return state.events.filter(evt => {
        //         return year >= evt.start_date && year >= evt.end_date;
        //     })
        // },
        eventByStartYear: (state) => (year) => {
            return state.events.filter(evt => {
                return new Date(evt.start_date).getFullYear() === year;
            })
        },
        // eventByName: (state) => (name) => {
        //     return state.events.filter(evt => {
        //         return evt.name === name;
        //     })[0]
        // },
        casesByYear: (state) => (year) => {
            return state.cases.filter(cas => {
                return year === new Date(cas.decision_date).getFullYear();
            })
        },
        templateCase: state => state.templateCase,
        timeline: (state) => {
            return {
                title: state.title,
                events: state.events,
                cases: state.cases,
                categories: state.categories
            }
        }
    },
    actions: {
        requestCreateTimeline: function ({commit}) {
            commit('setRequestStatus', 'pending');
            axios
                .post(this.state.urls.chronolawgic_api_create)
                .then(response => response.data)
                .then(new_tl => {
                    if (new_tl.status === "ok") {
                        this.dispatch('requestTimelineList');
                        router.push({name: 'timeline', params: {timeline: new_tl.id}})
                    }
                }).then(
                () => {
                    commit('setRequestStatusTerminal', 'success');
                    commit('setNotificationMessage', 'Timeline Created')
                }
            ).catch(error => {
                commit('setRequestStatusTerminal', 'error');
                commit('setNotificationMessage', error)
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
                () => {
                    commit('setRequestStatusTerminal', 'success');
                    commit('setNotificationMessage', "Timeline Deleted")
                }
            ).catch(error => {
                commit('setRequestStatusTerminal', 'error');
                commit('setNotificationMessage', error)
            })
        },
        requestUpdateTimeline: function ({commit}) {
            commit('setRequestStatus', 'pending');
            let json = JSON.stringify({timeline: this.getters.timeline})
            axios
                .post(this.state.urls.chronolawgic_api_update + this.state.id, json, {
                    headers: {
                        // Overwrite Axios's automatically set Content-Type
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.data)
                .then(
                () => {
                    commit('setRequestStatusTerminal', 'success');
                    commit('setNotificationMessage', "Timeline Saved")
                }
            ).catch(error => {
                commit('setRequestStatusTerminal', 'error');
                commit('setNotificationMessage', error)
            })
        },
        requestTimeline: function ({commit}, timelineId) {
            commit('setRequestStatus', 'pending');
            axios
                .get(this.state.urls.chronolawgic_api_retrieve + timelineId)
                .then(response => {
                    return response.data
                })
                .then(timeline => {
                    if (timeline.status === "ok") {
                        commit('setTimelineId', timeline['id'])
                        commit('setTimeline', timeline['timeline'])
                        commit('setCreatedBy', timeline['created_by'])
                        commit('setAuthor', timeline['is_owner'])
                    }
                }).then(
                () => {
                    commit('setRequestStatusTerminal', 'success');
                }
            ).catch(error => {
                commit('setRequestStatusTerminal', 'error');
                commit('setNotificationMessage', error)
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
                () => {
                    commit('setRequestStatusTerminal', 'success');
                }
            ).catch(error => {
                commit('setRequestStatusTerminal', 'error');
                commit('setNotificationMessage', error)
            })
        }
    }
});
export default store;