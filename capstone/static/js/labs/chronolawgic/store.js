import Vue from 'vue'
import Vuex from 'vuex'
import axios from "axios";

axios.defaults.xsrfHeaderName = "X-CSRFTOKEN";
axios.defaults.xsrfCookieName = "csrftoken";

// eslint-disable-next-line
const importUrls = urls; // defined in timeline.html
// eslint-disable-next-line
const importChoices = choices; // defined in timeline.html
// eslint-disable-next-line
const importUser = user; // defined in timeline.html

importChoices.colors = [
    "#00db67",
    "#ccff6d",
    "#dbc600",
    "#db8f00",
    "#ff8e7a",
    "#ff736c",
    "#e5435c",
    "#986d81",
    "#7e84ff",
    "#3656f6",
    "#2f2f2f",
    "#3e667a",
    "#00b7db",
    "#c4c4c4",
];

// jurisdictions
const jurisdictions = [];
for (let i = 0; i < importChoices.jurisdictions.length; i++) {
    jurisdictions.push(importChoices.jurisdictions[i][1])
}
importChoices.jurisdictions = jurisdictions;

// courts
const courts = [];
for (let i = 0; i < importChoices.courts.length; i++) {
    courts.push({
        slug: importChoices.courts[i][0],
        courtName: importChoices.courts[i][1]
    })
}
importChoices.courts = courts;

function getBestError(error) {
    // eslint-disable-next-line
    // debugger;
    if (error && Object.prototype.hasOwnProperty.call(error, "response") &&
        Object.prototype.hasOwnProperty.call(error.response, "data") &&
        Object.prototype.hasOwnProperty.call(error.response.data, "reason")) {
        if (Object.prototype.hasOwnProperty.call(error.response.data, "details")) {
            return error.response.data.reason + ": " + error.response.data.details
        }
        return error.response.data.reason
    }
    return error
}

Vue.use(Vuex);
const store = new Vuex.Store({
    state: {
        mobileEventsExpanded: false,
        breakPoint: 'lg',
        user: importUser,
        choices: importChoices,
        requestStatus: 'nominal', // can be nominal, success, error, or pending. Prone to race conditions, so use only for user feedback until its improved
        notificationMessage: null,
        urls: { // Doing this the long way to make it a little easier to see what's going on.
            chronolawgic_api_create: importUrls.chronolawgic_api_create,
            chronolawgic_api_retrieve: importUrls.chronolawgic_api_retrieve,
            chronolawgic_api_delete: importUrls.chronolawgic_api_delete,
            chronolawgic_update_timeline_metadata: importUrls.chronolawgic_update_timeline_metadata,
            chronolawgic_api_create_h2o: importUrls.chronolawgic_api_create_h2o,

            api_delete_subobject: importUrls.api_delete_subobject,
            api_add_update_subobject: importUrls.api_add_update_subobject,
            api_update_categories: importUrls.api_update_categories,

            static: importUrls.static,
            api_root: importUrls.api_root,
        },
        availableTimelines: [],
        minimized: true,
        id: 1,
        title: "",
        description: "",
        createdBy: -1, // (user accts are for auth/logging purposes)
        isAuthor: false,
        author: '', // user-added string
        categories: [],
        events: [],
        cases: [],
        stats: [],
        firstYear: 1900,
        lastYear: 2000,
        templateEvent: {
            name: "",
            short_description: "",
            long_description: "",
            start_date: "",
            end_date: "",
            url: "",
            color: "",
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
            color: "",
        },
        templateCategory: {
            name: "",
            shape: "",
            color: ""
        },
        missingCases: {}
    },
    mutations: {
        expandMobileEvents(state) {
            state.mobileEventsExpanded = true
        },
        setBreakPoint(state, newBreakPoint) {
            state.breakPoint = newBreakPoint
        },
        unExpandMobileEvents(state) {
            state.mobileEventsExpanded = false
        },
        toggleMinimized(state) {
            state.minimized = !state.minimized
        },
        setAvailableTimelines(state, json) {
            state.availableTimelines = json
        },
        setTimeline(state, json) {
            state.title = json.title;
            state.author = json.author ? json.author : "CAP User";
            state.description = json.description;
            state.categories = json.categories;
            state.events = json.events;
            state.cases = json.cases;
        },
        setTimelineId(state, timeline_id) {
            state.id = timeline_id;
        },
        setCreatedBy(state, createdBy) {
            state.createdBy = createdBy;
        },
        setAuthor(state, isAuthor) {
            state.isAuthor = isAuthor;
        },
        setCategories(state, categories) {
            state.categories = categories;
        },
        setStats(state, stats) {
            state.stats = stats;
        },
        setFirstYear(state, year) {
            state.firstYear = year;
        },
        setLastYear(state, year) {
            state.lastYear = year;
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
        addCase(state, case_object) {
            case_object.id = this.generateUUID();
            this.dispatch('requestAddUpdateSubobject', {'subobject_type': 'cases', 'subobject': case_object});
        },
        updateCase(state, case_object) {
            this.dispatch('requestAddUpdateSubobject', {'subobject_type':'cases', 'subobject': case_object});
        },
        deleteCase(state, id) {
            this.dispatch('requestDeleteSubobject', {'subobject_type':'cases', 'subobject_id': id});
        },
        addEvent(state, event_object) {
            event_object.id = this.generateUUID();
            this.dispatch('requestAddUpdateSubobject', {'subobject_type':'events', 'subobject': event_object});
        },
        updateEvent(state, event_object) {
            this.dispatch('requestAddUpdateSubobject', {'subobject_type':'events', 'subobject': event_object});
        },
        deleteEvent(state, id) {
            this.dispatch('requestDeleteSubobject', {'subobject_type':'events', 'subobject_id': id});
        },
        updateCategories(state, categories_list) {
            categories_list = categories_list.map((category) => {
                    if (!Object.prototype.hasOwnProperty.call(category, 'id')) {
                        category.id = this.generateUUID();
                    }
                    return category
            });
            this.dispatch('requestUpdateCategories', categories_list);
        },


        setMissingCases(state, missingCases) {
            state.missingCases = missingCases;
        }
    },
    getters: {
        breakPoint: state => state.breakPoint,
        isMobile: (state) => {
            return state.breakPoint === 'xs' || state.breakPoint === 'sm';
        },
        mobileEventsExpanded: state => state.mobileEventsExpanded,
        minimized: state => state.minimized,
        cases: state => state.cases,
        choices: state => state.choices,
        availableTimelines: state => state.availableTimelines,
        id: state => state.id,
        requestStatus: state => state.requestStatus,
        notificationMessage: state => state.notificationMessage,
        templateEvent: state => state.templateEvent,
        templateCase: state => state.templateCase,
        templateCategory: state => state.templateCategory,
        empty: (state) => {
            if (state.requestStatus === 'pending') {
                return 'pending'
            } else if (!Object.prototype.hasOwnProperty.call(state, 'events') &&
                !Object.prototype.hasOwnProperty.call(state, 'events') ) {
                return 'empty'
            } else if (!Object.prototype.hasOwnProperty.call(state, 'events')) {
                return state.cases.length === 0 ? 'empty' : 'populated'
            } else if (!Object.prototype.hasOwnProperty.call(state, 'cases') ) {
                return state.events.length === 0 ? 'empty' : 'populated'
            }
            return state.events.length + state.cases.length === 0 ? 'empty' : 'populated';
        },
        firstYear: (state) => {
            return state.firstYear;
        },
        lastYear: (state) => {
            return state.lastYear;
        },
        events: (state) => {
            return state.events.sort((a, b) => (a.start_date > b.start_date) ? 1 : -1)
        },
        eventByStartYear: (state) => (year) => {
            return state.events.filter(evt => {
                return new Date(evt.start_date).getUTCFullYear() === year;
            })
        },
        casesByYear: (state) => (year) => {
            return state.cases.filter(cas => {
                return year === new Date(cas.decision_date).getUTCFullYear();
            })
        },
        timeline: (state) => {
            return {
                title: state.title,
                author: state.author,
                events: state.events,
                cases: state.cases,
                categories: state.categories,
                description: state.description
            }
        },
        categories: (state) => {
            return state.categories
        },
        category: (state) => (id) => {
            return state.categories.find(cat => cat.id === id)
        },
        randomColor: (state) => {
            return state.colors[Math.floor(Math.random() * state.colors.length)]
        },
        stats: (state) => {
            return state.stats;
        },
        missingCases: (state) => {
            return state.missingCases;
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
                    }
                }).then(
                () => {
                    commit('setRequestStatusTerminal', 'success');
                    commit('setNotificationMessage', 'Timeline Created')
                }
            ).catch(error => {
                commit('setRequestStatusTerminal', 'error');
                commit('setNotificationMessage', "error creating timeline: " + getBestError(error))
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
                commit('setNotificationMessage', "error deleting timeline: " + getBestError(error))
            })
        },


         requestDeleteSubobject: function ({commit}, {subobject_type, subobject_id}) {
            commit('setRequestStatus', 'pending');

            let url = this.state.urls.api_delete_subobject
                .replace('__TIMELINE_ID__', this.state.id)
                .replace('__SUBOBJECT_ID__', subobject_id)
                .replace('__SUBOBJECT_TYPE__', subobject_type);

            return axios
                .delete(url, {
                    headers: {
                        // Overwrite Axios's automatically set Content-Type
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.data)
                .then(status => {
                        if (status.status == "ok") {
                            commit('setTimeline', status.timeline);
                            commit('setRequestStatusTerminal', 'success');
                            commit('setNotificationMessage', status.message)
                        }
                    }
                ).catch(error => {
                    commit('setRequestStatusTerminal', 'error');
                    commit('setNotificationMessage', "error updating timeline: " + getBestError(error))
            })
        },
        requestAddUpdateSubobject: function ({commit}, {subobject_type, subobject}) {
            commit('setRequestStatus', 'pending');
            let url = this.state.urls.api_add_update_subobject
                .replace('__TIMELINE_ID__', this.state.id)
                .replace('__SUBOBJECT_TYPE__', subobject_type);

            let update_payload = JSON.stringify(subobject);
            return axios
                .post(url, update_payload, {
                    headers: {
                        // Overwrite Axios's automatically set Content-Type
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.data)
                .then(status => {
                        if (status.status == "ok") {
                            commit('setTimeline', status.timeline);
                            commit('setRequestStatusTerminal', 'success');
                            commit('setNotificationMessage', status.message)
                        }
                    }
                ).catch(error => {
                    commit('setRequestStatusTerminal', 'error');
                    commit('setNotificationMessage', "error updating timeline: " + getBestError(error))
            })
        },
        requestUpdateCategories: function ({commit}, category_list) {
            commit('setRequestStatus', 'pending');
            let url = this.state.urls.api_update_categories
                .replace('__TIMELINE_ID__', this.state.id);
            let update_payload = JSON.stringify(category_list);
            return axios
                .post(url, update_payload, {
                    headers: {
                        // Overwrite Axios's automatically set Content-Type
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.data)
                .then(status => {
                        if (status.status == "ok") {
                            commit('setTimeline', status.timeline);
                            commit('setRequestStatusTerminal', 'success');
                            commit('setNotificationMessage', status.message)
                        }
                    }
                ).catch(error => {
                    commit('setRequestStatusTerminal', 'error');
                    commit('setNotificationMessage', "error updating categories: " + getBestError(error))
            })
        },
        requestTimeline: function ({commit}, timelineId) {
            // clear timeline if it exists
            commit('setTimelineId', '');
            commit('setTimeline', {title: ''});

            commit('setRequestStatus', 'pending');
            axios
                .get(this.state.urls.chronolawgic_api_retrieve + timelineId)
                .then(response => {
                    return response.data
                })
                .then(timeline => {
                    if (timeline.status === "ok") {
                        commit('setTimelineId', timeline['id']);
                        commit('setTimeline', timeline['timeline']);
                        commit('setCreatedBy', timeline['created_by']);
                        commit('setAuthor', timeline['is_owner'])
                        commit('setStats', timeline['stats'])
                        commit('setFirstYear', timeline['first_year'])
                        commit('setLastYear', timeline['last_year'])
                    }
                }).then(
                () => {
                    commit('setRequestStatusTerminal', 'success');
                }
            ).catch(error => {
                commit('setRequestStatusTerminal', 'error');
                commit('setNotificationMessage', "error retrieving timeline: " + getBestError(error))
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
                commit('setNotificationMessage', "error retrieving timeline list: " + getBestError(error))
            })
        },
        requestUpdateTimelineMetadata: function ({commit}, data) {
            commit('setRequestStatus', 'pending');
            let author = data.author.trim();
            let json = JSON.stringify({
                title: data.title,
                author: author,
                description: data.description,
            });

            return axios
                .post(this.state.urls.chronolawgic_update_timeline_metadata + data.id, json, {
                    headers: {
                        // Overwrite Axios's automatically set Content-Type
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.data)
                .then(
                    () => {
                        commit('setRequestStatusTerminal', 'success');
                        commit('setNotificationMessage', "Change Saved")
                    }
                ).catch(error => {
                    commit('setRequestStatusTerminal', 'error');
                    commit('setNotificationMessage', "error updating timeline: " + getBestError(error))
                })
        },
        requestCreateH2OTimeline: function ({commit}, data) {
            let json = JSON.stringify(data)
            return axios.post(this.state.urls.chronolawgic_api_create_h2o, json, {
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => response.data)
                .then(
                    (new_tl) => {
                        if (new_tl.status === "ok") {
                            this.dispatch('requestTimelineList');
                        }
                        commit('setRequestStatusTerminal', 'success');
                        commit('setNotificationMessage', "Timeline Created")
                        return new_tl
                    }
                ).catch(error => {
                    commit('setRequestStatusTerminal', 'error');
                    commit('setNotificationMessage', "error creating timeline: " + getBestError(error))
                    return error
                })

        }
    }
});

store.generateUUID = () => {
    // https://stackoverflow.com/a/2117523/2247227
    return 'xxxxxxxxxx'.replace(/[xy]/g, function (c) {
        let r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}


export default store;